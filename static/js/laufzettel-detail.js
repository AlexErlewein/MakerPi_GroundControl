/**
 * Render a QR code into a container element using qrcode-generator.
 * @param {HTMLElement} container
 * @param {string} text
 * @param {number} size  pixel size (width = height)
 * @param {'L'|'M'|'Q'|'H'} ecLevel  error correction level (use 'L' for EPC)
 */
function makeQR(container, text, size, ecLevel) {
  container.innerHTML = "";
  const qr = qrcode(0, ecLevel || "M");  // typeNumber 0 = auto-detect
  qr.addData(text);
  qr.make();
  const cellSize = Math.floor(size / (qr.getModuleCount() + 8));
  const margin = Math.floor((size - cellSize * qr.getModuleCount()) / 2);
  container.innerHTML = qr.createImgTag(cellSize, margin);
  const img = container.querySelector("img");
  if (img) { img.style.width = size + "px"; img.style.height = size + "px"; }
}

let currentData = null;
let editingMaterialId = null;
let katalog = [];
let currentMatMode = "freitext";
let selectedVariante = null;
let selectedKategorie = null;
let logoDataUrl = null;
let paymentConfig = { sumup_configured: false };

// ── Origin awareness (from= param) ─────────────────────────
const _fromParam = new URLSearchParams(window.location.search).get("from");
if (_fromParam) {
  const backLink = document.getElementById("back-link");
  if (backLink) {
    if (_fromParam === "kasse") {
      backLink.href = "/kasse";
      backLink.textContent = "← Zurück zur Kasse";
    } else if (_fromParam === "member") {
      backLink.href = "/member/laufzettel";
      backLink.textContent = "← Zurück zum Auftrag";
    }
  }
}

// ── Data loading ─────────────────────────────────────────────

async function loadLogo() {
  try {
    const res = await fetch("/graphics/H3ckeLogo.svg");
    const svg = await res.text();
    const b64 = btoa(unescape(encodeURIComponent(svg)));
    logoDataUrl = `data:image/svg+xml;base64,${b64}`;
  } catch (e) {
    logoDataUrl = null;
  }
}

async function loadDetail() {
  try {
    const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}`);
    if (!res.ok) {
      document.querySelector("main").innerHTML =
        '<p style="color:var(--danger);padding:20px;">Laufzettel not found.</p>';
      return;
    }
    currentData = await res.json();
    renderInfo();
    renderNodes();
    renderMaterial();
  } catch (e) {
    console.error("loadDetail failed:", e);
    document.querySelector("main").innerHTML =
      '<p style="color:var(--danger);padding:20px;">Fehler beim Laden: ' + e.message + "</p>";
  }
}

async function loadKatalog() {
  const res = await fetch("/api/katalog");
  katalog = await res.json();
  populateLocationSelect();
}

async function loadPaymentConfig() {
  try {
    const res = await fetch("/api/payment/config");
    if (res.ok) paymentConfig = await res.json();
  } catch (_) {}
}

// ── Info rendering ───────────────────────────────────────────

function renderInfo() {
  const d = currentData;
  document.getElementById("lz-id-display").textContent = `#${d.id}`;
  document.getElementById("view-lz-nr").textContent = d.id || "-";
  document.getElementById("view-date").textContent = d.date || "-";
  document.getElementById("view-start").textContent = d.start ? new Date(d.start).toLocaleString() : "-";
  document.getElementById("view-owner").textContent = d.owner_name || "-";
  document.getElementById("view-member-id").textContent = d.member_id || "-";
  document.getElementById("view-uid").textContent = d.uid || "-";
  const locked = !!d.payment_method;
  document.getElementById("edit-info-btn").style.display = locked ? "none" : "";
  document.getElementById("delete-lz-btn").style.display = locked ? "none" : "";
  document.getElementById("add-spende-btn").style.display = locked ? "none" : "";
  document.getElementById("add-aufrunden-btn").style.display = locked ? "none" : "";
  document.getElementById("add-material-btn").style.display = locked ? "none" : "";
}

function renderNodes() {
  const container = document.getElementById("nodes-container");
  const nodes = currentData.nodes || [];
  if (nodes.length === 0) {
    container.innerHTML = '<span style="color:var(--text-secondary)">No nodes recorded yet.</span>';
    return;
  }
  container.innerHTML = nodes.map((n) => `<span class="node-chip">${esc(n)}</span>`).join("");
}

function toggleNodes() {
  const container = document.getElementById("nodes-container");
  const btn = document.getElementById("toggle-nodes-btn");
  if (container.style.display === "none") {
    container.style.display = "block";
    btn.textContent = "▲";
  } else {
    container.style.display = "none";
    btn.textContent = "▼";
  }
}

// Groups: Spende items go to "Spenden" (rendered last); others group by location, then category within location.
function getMatGroupKey(m) {
  if (m.is_spende) return "__spenden__";
  const loc = getLocationForVariante(m.variante_id);
  const cat = getKategorieForVariante(m.variante_id);
  return { loc: loc || "Freitext", cat: cat || "" };
}
function sortMats(mats) {
  return [...mats].sort((a, b) => {
    const sA = !!a.is_spende,
      sB = !!b.is_spende;
    if (sA !== sB) return sA ? 1 : -1;
    const locA = getLocationForVariante(a.variante_id) || "￿";
    const locB = getLocationForVariante(b.variante_id) || "￿";
    const catA = getKategorieForVariante(a.variante_id) || "";
    const catB = getKategorieForVariante(b.variante_id) || "";
    return locA.localeCompare(locB) || catA.localeCompare(catB) || a.name.localeCompare(b.name);
  });
}

function renderMaterial() {
  const tbody = document.getElementById("material-body");
  const mats = [...(currentData.material || [])];
  if (mats.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty">No material entries yet.</td></tr>';
    return;
  }
  const sorted = sortMats(mats);
  let rowIndex = 0;
  let lastLoc = undefined;
  let lastCat = undefined;
  const rows = [];
  for (const m of sorted) {
    const groupKey = getMatGroupKey(m);
    if (m.is_spende) {
      if (lastLoc !== "__spenden__") {
        rows.push(`<tr class="location-separator"><td colspan="7"><span>Spenden</span></td></tr>`);
        lastLoc = "__spenden__";
        lastCat = undefined;
      }
    } else {
      const loc = groupKey.loc;
      const cat = groupKey.cat;
      if (loc !== lastLoc) {
        rows.push(`<tr class="location-separator"><td colspan="7"><span>${esc(loc)}</span></td></tr>`);
        lastLoc = loc;
        lastCat = undefined;
      }
      if (cat !== lastCat && cat) {
        rows.push(`<tr class="category-separator"><td colspan="7"><span>${esc(cat)}</span></td></tr>`);
        lastCat = cat;
      }
    }
    rowIndex++;
    const mengeCell = buildMengeDisplay(m);
    const priceCell =
      m.calculated_price != null
        ? `<span class="price-col">${m.calculated_price.toFixed(2)} €</span>`
        : '<span style="color:var(--text-secondary)">-</span>';
    const unitPriceLabel =
      getUnitPriceLabel(m.variante_id) ||
      (m.calculated_price != null && m.menge
        ? `${(m.calculated_price / m.menge).toFixed(4)} €/${m.unit || "Stk"}`
        : null);
    rows.push(`
        <tr>
            <td>${rowIndex}</td>
            <td>${esc(m.name)}</td>
            <td>${mengeCell}</td>
            <td>${esc(m.unit || "-")}</td>
            <td style="color:var(--text-secondary);font-size:0.85rem;white-space:nowrap;">${unitPriceLabel || "-"}</td>
            <td>${priceCell}</td>
            <td class="actions">
                <button class="btn btn-sm btn-secondary" onclick="openEditMaterial(${m.id})">Bearbeiten</button>
                <button class="btn btn-sm btn-danger" onclick="deleteMaterial(${m.id})">Löschen</button>
            </td>
        </tr>`);
  }
  tbody.innerHTML = rows.join("");

  const total = mats.reduce((sum, m) => sum + (m.calculated_price != null ? m.calculated_price : 0), 0);
  const hasAnyPrice = mats.some((m) => m.calculated_price != null);
  const tfoot = document.getElementById("material-total");
  if (hasAnyPrice) {
    document.getElementById("material-total-value").textContent = `${total.toFixed(2)} €`;
    tfoot.classList.remove("hidden");
  } else {
    tfoot.classList.add("hidden");
  }
  renderPaymentSection(total, hasAnyPrice);
}

function buildMengeDisplay(m) {
  if (m.laenge_cm != null && m.breite_cm != null && m.hoehe_cm != null) {
    const vol = m.laenge_cm * m.breite_cm * m.hoehe_cm;
    return `${m.laenge_cm}×${m.breite_cm}×${m.hoehe_cm} cm <span style="color:var(--text-secondary);font-size:0.8rem;">(${vol.toFixed(1)} cm³)</span>`;
  }
  return m.menge != null ? String(m.menge) : "-";
}

function getUkatAndVariante(varianteId) {
  if (!varianteId) return null;
  for (const loc of katalog) {
    for (const kat of loc.kategorien || []) {
      for (const ukat of kat.unterkategorien || []) {
        for (const v of ukat.varianten || []) {
          if (v.id === varianteId) return { ukat, variante: v, loc };
        }
      }
    }
  }
  return null;
}

// Legacy alias kept for any call-sites that use the old name
function getKatAndVariante(varianteId) {
  const found = getUkatAndVariante(varianteId);
  if (!found) return null;
  return { kat: found.ukat, variante: found.variante };
}

function getUnitPriceLabel(varianteId) {
  const found = getUkatAndVariante(varianteId);
  if (!found) return null;
  const { ukat, variante } = found;
  const pm = variante.pricing_model || ukat.pricing_model;
  const suffix =
    pm === "per_gram"
      ? "/gr"
      : pm === "per_kilogram"
        ? "/kg"
        : pm === "per_volume_cm3"
          ? "/cm³"
          : pm === "per_volume_l"
            ? "/L"
            : pm === "per_cubic_meter"
              ? "/m³"
              : pm === "per_cubic_deci_meter"
                ? "/dm³"
                : pm === "per_volume_m3"
                  ? "/m³"
                  : pm === "per_area_m2"
                    ? "/m²"
                    : pm === "per_area_dm2"
                      ? "/dm²"
                      : pm === "per_minute"
                        ? "/min"
                        : pm === "per_hour"
                          ? "/h"
                          : `/${variante.unit || ukat.unit || "Stück"}`;
  return `${variante.price.toFixed(2)} €${suffix}`;
}

function getLocationForVariante(varianteId) {
  if (!varianteId) return null;
  for (const loc of katalog) {
    for (const kat of loc.kategorien || []) {
      for (const ukat of kat.unterkategorien || []) {
        for (const v of ukat.varianten || []) {
          if (v.id === varianteId) return loc.name;
        }
      }
    }
  }
  return null;
}

function getKategorieForVariante(varianteId) {
  if (!varianteId) return null;
  for (const loc of katalog) {
    for (const kat of loc.kategorien || []) {
      for (const ukat of kat.unterkategorien || []) {
        for (const v of ukat.varianten || []) {
          if (v.id === varianteId) return kat.name;
        }
      }
    }
  }
  return null;
}

function esc(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildMengeText(m) {
  if (m.laenge_cm != null && m.breite_cm != null && m.hoehe_cm != null) {
    const vol = m.laenge_cm * m.breite_cm * m.hoehe_cm;
    return `${m.laenge_cm}×${m.breite_cm}×${m.hoehe_cm} cm (${vol.toFixed(1)} cm³)`;
  }
  return m.menge != null ? String(m.menge) : "-";
}

// ── Info edit ────────────────────────────────────────────────

document.getElementById("edit-info-btn").addEventListener("click", () => {
  const d = currentData;
  document.getElementById("edit-owner").value = d.owner_name || "";
  document.getElementById("edit-member-id").value = d.member_id || "";
  if (d.start) {
    const dt = new Date(d.start);
    const local = new Date(dt.getTime() - dt.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    document.getElementById("edit-start").value = local;
  } else {
    document.getElementById("edit-start").value = "";
  }
  document.getElementById("info-view").classList.add("hidden");
  document.getElementById("info-edit-form").classList.remove("hidden");
  document.getElementById("edit-info-btn").classList.add("hidden");
});

document.getElementById("cancel-edit-btn").addEventListener("click", cancelInfoEdit);

function cancelInfoEdit() {
  document.getElementById("info-view").classList.remove("hidden");
  document.getElementById("info-edit-form").classList.add("hidden");
  document.getElementById("edit-info-btn").classList.remove("hidden");
}

document.getElementById("info-edit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {};
  const owner = document.getElementById("edit-owner").value.trim();
  const memberId = document.getElementById("edit-member-id").value.trim();
  const start = document.getElementById("edit-start").value;
  if (owner) body.owner_name = owner;
  if (memberId) body.member_id = memberId;
  if (start) body.start = new Date(start).toISOString();

  const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    currentData = await res.json();
    renderInfo();
    cancelInfoEdit();
  } else {
    const err = await res.json();
    alert("Error: " + (err.detail || "Failed to save"));
  }
});

// ── Material modal ───────────────────────────────────────────

function setMatMode(mode) {
  currentMatMode = mode;
  document.getElementById("mode-freitext-btn").classList.toggle("active", mode === "freitext");
  document.getElementById("mode-katalog-btn").classList.toggle("active", mode === "katalog");
  document.getElementById("freitext-fields").classList.toggle("hidden", mode !== "freitext");
  document.getElementById("katalog-fields").classList.toggle("hidden", mode !== "katalog");
  if (mode === "katalog") resetKatalogFields();
}

function openAddMaterial() {
  editingMaterialId = null;
  selectedVariante = null;
  selectedKategorie = null;
  document.getElementById("modal-title").textContent = "Material hinzufügen";
  document.getElementById("material-form").reset();
  document.getElementById("edit-material-id").value = "";
  document.getElementById("edit-mat-variante-id").value = "";
  document.getElementById("field-mat-unit-price").value = "";
  document.getElementById("field-mat-total-price").value = "";
  document.getElementById("field-mat-tax-rate").value = "19";
  setMatMode("katalog");
  document.getElementById("material-modal").classList.remove("hidden");
  document.getElementById("field-mat-name").focus();
}

function openEditMaterial(id) {
  const mat = (currentData.material || []).find((m) => m.id === id);
  if (!mat) return;
  editingMaterialId = id;
  selectedVariante = null;
  selectedKategorie = null;
  document.getElementById("modal-title").textContent = "Material bearbeiten";
  document.getElementById("edit-material-id").value = id;
  document.getElementById("edit-mat-variante-id").value = mat.variante_id || "";

  // Always open in freitext for editing (simpler)
  setMatMode("freitext");
  document.getElementById("field-mat-name").value = mat.name || "";
  document.getElementById("field-mat-menge").value = mat.menge != null ? mat.menge : "";
  document.getElementById("field-mat-unit").value = mat.unit || "";
  if (mat.calculated_price != null) {
    document.getElementById("field-mat-total-price").value = mat.calculated_price;
    if (mat.menge) {
      document.getElementById("field-mat-unit-price").value = parseFloat((mat.calculated_price / mat.menge).toFixed(6));
    } else {
      document.getElementById("field-mat-unit-price").value = "";
    }
  } else {
    document.getElementById("field-mat-unit-price").value = "";
    document.getElementById("field-mat-total-price").value = "";
  }
  document.getElementById("field-mat-tax-rate").value = String(mat.tax_rate != null ? mat.tax_rate : 19);
  document.getElementById("material-modal").classList.remove("hidden");
  document.getElementById("field-mat-name").focus();
}

function closeModal() {
  document.getElementById("material-modal").classList.add("hidden");
  editingMaterialId = null;
  selectedVariante = null;
  selectedKategorie = null;
}

// ── Catalog cascading selects ─────────────────────────────────

function populateLocationSelect() {
  const sel = document.getElementById("kat-select-location");
  sel.innerHTML =
    '<option value="">-- Standort wählen --</option>' +
    katalog.map((l) => `<option value="${l.id}">${esc(l.name)}</option>`).join("");
}

function onKatLocationChange() {
  const locId = parseInt(document.getElementById("kat-select-location").value);
  const katSel = document.getElementById("kat-select-kategorie");
  const varSel = document.getElementById("kat-select-variante");

  katSel.innerHTML = '<option value="">-- Kategorie wählen --</option>';
  varSel.innerHTML = '<option value="">-- Variante wählen --</option>';
  varSel.disabled = true;
  selectedVariante = null;
  selectedKategorie = null;
  hideKatInputFields();
  hidePricePreview();

  if (!locId) {
    katSel.disabled = true;
    return;
  }
  const loc = katalog.find((l) => l.id === locId);
  if (!loc) {
    katSel.disabled = true;
    return;
  }

  katSel.innerHTML =
    '<option value="">-- Kategorie wählen --</option>' +
    (loc.kategorien || []).map((k) => `<option value="${k.id}">${esc(k.name)}</option>`).join("");
  katSel.disabled = false;
}

function onKatKategorieChange() {
  const locId = parseInt(document.getElementById("kat-select-location").value);
  const katId = parseInt(document.getElementById("kat-select-kategorie").value);
  const ukatSel = document.getElementById("kat-select-unterkategorie");
  const varSel = document.getElementById("kat-select-variante");

  ukatSel.innerHTML = '<option value="">-- Unterkategorie wählen --</option>';
  ukatSel.disabled = true;
  varSel.innerHTML = '<option value="">-- Variante wählen --</option>';
  varSel.disabled = true;
  selectedVariante = null;
  selectedKategorie = null;
  hideKatInputFields();
  hidePricePreview();

  if (!katId) return;
  const loc = katalog.find((l) => l.id === locId);
  const kat = loc && loc.kategorien ? loc.kategorien.find((k) => k.id === katId) : undefined;
  if (!kat) return;

  ukatSel.innerHTML =
    '<option value="">-- Unterkategorie wählen --</option>' +
    (kat.unterkategorien || []).map((u) => `<option value="${u.id}">${esc(u.name)}</option>`).join("");
  ukatSel.disabled = false;
}

function onKatUnterkategorieChange() {
  const locId = parseInt(document.getElementById("kat-select-location").value);
  const katId = parseInt(document.getElementById("kat-select-kategorie").value);
  const ukatId = parseInt(document.getElementById("kat-select-unterkategorie").value);
  const varSel = document.getElementById("kat-select-variante");

  varSel.innerHTML = '<option value="">-- Variante wählen --</option>';
  varSel.disabled = true;
  selectedVariante = null;
  selectedKategorie = null;
  hideKatInputFields();
  hidePricePreview();

  if (!ukatId) return;
  const loc = katalog.find((l) => l.id === locId);
  const kat = loc && loc.kategorien ? loc.kategorien.find((k) => k.id === katId) : undefined;
  const ukat = kat && kat.unterkategorien ? kat.unterkategorien.find((u) => u.id === ukatId) : undefined;
  if (!ukat) return;

  selectedKategorie = ukat; // selectedKategorie now holds the unterkategorie
  const pm = ukat.pricing_model;
  const suffix =
    pm === "per_gram"
      ? "/gr"
      : pm === "per_kilogram"
        ? "/kg"
        : pm === "per_volume_cm3"
          ? "/cm³"
          : pm === "per_volume_l"
            ? "/L"
            : pm === "per_cubic_meter"
              ? "/m³"
              : pm === "per_cubic_deci_meter"
                ? "/dm³"
                : pm === "per_volume_m3"
                  ? "/m³"
                  : pm === "per_area_m2"
                    ? "/m²"
                    : pm === "per_area_dm2"
                      ? "/dm²"
                      : pm === "per_minute"
                        ? "/min"
                        : pm === "per_hour"
                          ? "/h"
                          : `/${ukat.unit || "Stück"}`;
  varSel.innerHTML =
    '<option value="">-- Variante wählen --</option>' +
    (ukat.varianten || [])
      .map((v) => `<option value="${v.id}">${esc(v.name)} (${v.price.toFixed(4)} €${suffix})</option>`)
      .join("");
  varSel.disabled = false;
  // Don't show input fields until a variant is selected, since pricing models are now on variants
  hideKatInputFields();
}

function onKatVarianteChange() {
  const varId = parseInt(document.getElementById("kat-select-variante").value);
  hidePricePreview();
  if (!varId || !selectedKategorie) {
    selectedVariante = null;
    return;
  }
  selectedVariante =
    (selectedKategorie.varianten ? selectedKategorie.varianten.find((v) => v.id === varId) : null) || null;
  if (selectedVariante) {
    showKatInputFields(selectedVariante.pricing_model || "per_unit", selectedVariante.unit);
  }
  recalcPrice();
}

function showKatInputFields(pricingModel, unit) {
  const isVolume =
    pricingModel === "per_volume_cm3" ||
    pricingModel === "per_cubic_meter" ||
    pricingModel === "per_cubic_deci_meter" ||
    pricingModel === "per_volume_m3";
  const isWeight = pricingModel === "per_gram" || pricingModel === "per_kilogram";
  const isArea = pricingModel === "per_area_m2" || pricingModel === "per_area_dm2";
  document.getElementById("kat-fields-gram").classList.toggle("hidden", !isWeight && pricingModel !== "per_volume_l");
  document.getElementById("kat-fields-volume").classList.toggle("hidden", !isVolume);
  document.getElementById("kat-fields-area").classList.toggle("hidden", !isArea);
  document.getElementById("kat-fields-minute").classList.toggle("hidden", pricingModel !== "per_minute" && pricingModel !== "per_hour");
  document.getElementById("kat-fields-unit").classList.toggle("hidden", pricingModel !== "per_unit");
  const unitLabel = unit
    ? `(${unit})`
    : pricingModel === "per_kilogram"
      ? "(kg)"
      : pricingModel === "per_gram"
        ? "(g)"
        : pricingModel === "per_cubic_meter"
          ? "(m³)"
          : pricingModel === "per_cubic_deci_meter"
            ? "(dm³)"
            : pricingModel === "per_volume_m3"
              ? "(m³)"
              : pricingModel === "per_area_m2"
                ? "(m²)"
                : pricingModel === "per_area_dm2"
                  ? "(dm²)"
                  : pricingModel === "per_minute"
                    ? "(min)"
                    : pricingModel === "per_hour"
                      ? "(h)"
                      : pricingModel === "per_volume_l"
                      ? "(L)"
                      : "";
  document.getElementById("kat-gram-label").textContent = unitLabel;
  document.getElementById("kat-unit-label").textContent = unitLabel;
  // attach live recalc listeners
  [
    "kat-menge-gram",
    "kat-menge-minute",
    "kat-menge-unit",
    "kat-laenge",
    "kat-breite",
    "kat-hoehe",
    "kat-area-laenge",
    "kat-area-breite",
  ].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.oninput = recalcPrice;
  });
}

function hideKatInputFields() {
  ["kat-fields-gram", "kat-fields-volume", "kat-fields-area", "kat-fields-minute", "kat-fields-unit"].forEach((id) =>
    document.getElementById(id).classList.add("hidden"),
  );
}

function recalcPrice() {
  if (!selectedVariante || !selectedKategorie) {
    hidePricePreview();
    return;
  }
  const pm = selectedVariante.pricing_model || "per_unit";
  let price = null;

  if (pm === "per_gram") {
    const menge = parseFloat(document.getElementById("kat-menge-gram").value);
    if (!isNaN(menge) && menge > 0) price = menge * selectedVariante.price;
  } else if (pm === "per_kilogram") {
    const menge = parseFloat(document.getElementById("kat-menge-gram").value);
    if (!isNaN(menge) && menge > 0) price = menge * selectedVariante.price;
  } else if (pm === "per_volume_cm3") {
    const l = parseFloat(document.getElementById("kat-laenge").value);
    const b = parseFloat(document.getElementById("kat-breite").value);
    const h = parseFloat(document.getElementById("kat-hoehe").value);
    if (!isNaN(l) && !isNaN(b) && !isNaN(h) && l > 0 && b > 0 && h > 0) {
      price = l * b * h * selectedVariante.price;
    }
  } else if (pm === "per_volume_l") {
    const liters = parseFloat(document.getElementById("kat-menge-gram").value);
    if (!isNaN(liters) && liters > 0) {
      price = liters * selectedVariante.price;
    }
  } else if (pm === "per_cubic_meter") {
    const l = parseFloat(document.getElementById("kat-laenge").value);
    const b = parseFloat(document.getElementById("kat-breite").value);
    const h = parseFloat(document.getElementById("kat-hoehe").value);
    if (!isNaN(l) && !isNaN(b) && !isNaN(h) && l > 0 && b > 0 && h > 0) {
      price = ((l * b * h) / 1000000) * selectedVariante.price;
    }
  } else if (pm === "per_cubic_deci_meter") {
    const l = parseFloat(document.getElementById("kat-laenge").value);
    const b = parseFloat(document.getElementById("kat-breite").value);
    const h = parseFloat(document.getElementById("kat-hoehe").value);
    if (!isNaN(l) && !isNaN(b) && !isNaN(h) && l > 0 && b > 0 && h > 0) {
      price = ((l * b * h) / 1000) * selectedVariante.price;
    }
  } else if (pm === "per_volume_m3") {
    const l = parseFloat(document.getElementById("kat-laenge").value);
    const b = parseFloat(document.getElementById("kat-breite").value);
    const h = parseFloat(document.getElementById("kat-hoehe").value);
    if (!isNaN(l) && !isNaN(b) && !isNaN(h) && l > 0 && b > 0 && h > 0) {
      price = ((l * b * h) / 1000000) * selectedVariante.price;
    }
  } else if (pm === "per_area_m2") {
    const l = parseFloat(document.getElementById("kat-area-laenge").value);
    const b = parseFloat(document.getElementById("kat-area-breite").value);
    if (!isNaN(l) && !isNaN(b) && l > 0 && b > 0) {
      price = ((l * b) / 10000) * selectedVariante.price;
    }
  } else if (pm === "per_area_dm2") {
    const l = parseFloat(document.getElementById("kat-area-laenge").value);
    const b = parseFloat(document.getElementById("kat-area-breite").value);
    if (!isNaN(l) && !isNaN(b) && l > 0 && b > 0) {
      price = ((l * b) / 100) * selectedVariante.price;
    }
  } else if (pm === "per_minute") {
    const menge = parseFloat(document.getElementById("kat-menge-minute").value);
    if (!isNaN(menge) && menge > 0) price = menge * selectedVariante.price;
  } else if (pm === "per_hour") {
    const menge = parseFloat(document.getElementById("kat-menge-minute").value);
    if (!isNaN(menge) && menge > 0) price = menge * selectedVariante.price;
  } else if (pm === "per_unit") {
    const menge = parseFloat(document.getElementById("kat-menge-unit").value);
    if (!isNaN(menge) && menge > 0) price = menge * selectedVariante.price;
  }

  if (price !== null) {
    document.getElementById("price-value").textContent = `${price.toFixed(2)} €`;
    document.getElementById("price-preview").classList.remove("hidden");
  } else {
    hidePricePreview();
  }
}

function hidePricePreview() {
  document.getElementById("price-preview").classList.add("hidden");
}

function resetKatalogFields() {
  document.getElementById("kat-select-location").value = "";
  document.getElementById("kat-select-kategorie").innerHTML = '<option value="">-- Kategorie wählen --</option>';
  document.getElementById("kat-select-kategorie").disabled = true;
  document.getElementById("kat-select-unterkategorie").innerHTML =
    '<option value="">-- Unterkategorie wählen --</option>';
  document.getElementById("kat-select-unterkategorie").disabled = true;
  document.getElementById("kat-select-variante").innerHTML = '<option value="">-- Variante wählen --</option>';
  document.getElementById("kat-select-variante").disabled = true;
  hideKatInputFields();
  hidePricePreview();
  selectedVariante = null;
  selectedKategorie = null;
}

// ── Material form submit ──────────────────────────────────────

document.getElementById("material-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  let body = {};

  if (currentMatMode === "freitext") {
    const totalPrice = parseFloat(document.getElementById("field-mat-total-price").value);
    body = {
      name: document.getElementById("field-mat-name").value.trim(),
      menge: parseFloat(document.getElementById("field-mat-menge").value) || null,
      unit: document.getElementById("field-mat-unit").value.trim() || null,
      calculated_price: !isNaN(totalPrice) && totalPrice >= 0 ? parseFloat(totalPrice.toFixed(4)) : null,
      tax_rate: parseFloat(document.getElementById("field-mat-tax-rate").value),
    };
  } else {
    // Katalog mode
    if (!selectedVariante || !selectedKategorie) {
      alert("Bitte Standort, Kategorie und Variante auswählen.");
      return;
    }
    const pm = selectedVariante.pricing_model || "per_unit";
    body.variante_id = selectedVariante.id;
    body.unit = selectedVariante.unit || null;
    body.name = `${selectedKategorie.name} – ${selectedVariante.name}`;
    body.tax_rate = selectedKategorie.tax_rate != null ? selectedKategorie.tax_rate : 19;

    if (pm === "per_gram") {
      const menge = parseFloat(document.getElementById("kat-menge-gram").value);
      if (isNaN(menge) || menge <= 0) {
        alert("Bitte gültige Menge eingeben.");
        return;
      }
      body.menge = menge;
      body.calculated_price = parseFloat((menge * selectedVariante.price).toFixed(4));
    } else if (pm === "per_kilogram") {
      const menge = parseFloat(document.getElementById("kat-menge-gram").value);
      if (isNaN(menge) || menge <= 0) {
        alert("Bitte gültige Menge eingeben.");
        return;
      }
      body.menge = menge;
      body.unit = selectedKategorie.unit || "kg";
      body.calculated_price = parseFloat((menge * selectedVariante.price).toFixed(4));
    } else if (pm === "per_volume_cm3") {
      const l = parseFloat(document.getElementById("kat-laenge").value);
      const b = parseFloat(document.getElementById("kat-breite").value);
      const h = parseFloat(document.getElementById("kat-hoehe").value);
      if ([l, b, h].some((v) => isNaN(v) || v <= 0)) {
        alert("Bitte alle Maße eingeben.");
        return;
      }
      body.laenge_cm = l;
      body.breite_cm = b;
      body.hoehe_cm = h;
      body.calculated_price = parseFloat((l * b * h * selectedVariante.price).toFixed(4));
    } else if (pm === "per_volume_l") {
      const liters = parseFloat(document.getElementById("kat-menge-gram").value);
      if (isNaN(liters) || liters <= 0) {
        alert("Bitte gültige Menge in Litern eingeben.");
        return;
      }
      body.menge = liters;
      body.unit = selectedKategorie.unit || "L";
      body.calculated_price = parseFloat((liters * selectedVariante.price).toFixed(4));
    } else if (pm === "per_cubic_meter") {
      const l = parseFloat(document.getElementById("kat-laenge").value);
      const b = parseFloat(document.getElementById("kat-breite").value);
      const h = parseFloat(document.getElementById("kat-hoehe").value);
      if ([l, b, h].some((v) => isNaN(v) || v <= 0)) {
        alert("Bitte alle Maße eingeben.");
        return;
      }
      body.laenge_cm = l;
      body.breite_cm = b;
      body.hoehe_cm = h;
      body.calculated_price = parseFloat((((l * b * h) / 1000000) * selectedVariante.price).toFixed(4));
    } else if (pm === "per_cubic_deci_meter") {
      const l = parseFloat(document.getElementById("kat-laenge").value);
      const b = parseFloat(document.getElementById("kat-breite").value);
      const h = parseFloat(document.getElementById("kat-hoehe").value);
      if ([l, b, h].some((v) => isNaN(v) || v <= 0)) {
        alert("Bitte alle Maße eingeben.");
        return;
      }
      body.laenge_cm = l;
      body.breite_cm = b;
      body.hoehe_cm = h;
      body.calculated_price = parseFloat((((l * b * h) / 1000) * selectedVariante.price).toFixed(4));
    } else if (pm === "per_volume_m3") {
      const l = parseFloat(document.getElementById("kat-laenge").value);
      const b = parseFloat(document.getElementById("kat-breite").value);
      const h = parseFloat(document.getElementById("kat-hoehe").value);
      if ([l, b, h].some((v) => isNaN(v) || v <= 0)) {
        alert("Bitte alle Maße eingeben.");
        return;
      }
      body.laenge_cm = l;
      body.breite_cm = b;
      body.hoehe_cm = h;
      body.calculated_price = parseFloat((((l * b * h) / 1000000) * selectedVariante.price).toFixed(4));
    } else if (pm === "per_area_m2") {
      const l = parseFloat(document.getElementById("kat-area-laenge").value);
      const b = parseFloat(document.getElementById("kat-area-breite").value);
      if ([l, b].some((v) => isNaN(v) || v <= 0)) {
        alert("Bitte Länge und Breite eingeben.");
        return;
      }
      body.laenge_cm = l;
      body.breite_cm = b;
      body.calculated_price = parseFloat((((l * b) / 10000) * selectedVariante.price).toFixed(4));
    } else if (pm === "per_area_dm2") {
      const l = parseFloat(document.getElementById("kat-area-laenge").value);
      const b = parseFloat(document.getElementById("kat-area-breite").value);
      if ([l, b].some((v) => isNaN(v) || v <= 0)) {
        alert("Bitte Länge und Breite eingeben.");
        return;
      }
      body.laenge_cm = l;
      body.breite_cm = b;
      body.calculated_price = parseFloat((((l * b) / 100) * selectedVariante.price).toFixed(4));
    } else if (pm === "per_minute") {
      const menge = parseFloat(document.getElementById("kat-menge-minute").value);
      if (isNaN(menge) || menge <= 0) {
        alert("Bitte gültige Dauer eingeben.");
        return;
      }
      body.menge = menge;
      body.unit = "min";
      body.calculated_price = parseFloat((menge * selectedVariante.price).toFixed(4));
    } else if (pm === "per_hour") {
      const menge = parseFloat(document.getElementById("kat-menge-minute").value);
      if (isNaN(menge) || menge <= 0) {
        alert("Bitte gültige Dauer eingeben.");
        return;
      }
      body.menge = menge;
      body.unit = "h";
      body.calculated_price = parseFloat((menge * selectedVariante.price).toFixed(4));
    } else {
      const menge = parseFloat(document.getElementById("kat-menge-unit").value);
      if (isNaN(menge) || menge <= 0) {
        alert("Bitte gültige Menge eingeben.");
        return;
      }
      body.menge = menge;
      body.calculated_price = parseFloat((menge * selectedVariante.price).toFixed(4));
    }
  }

  let res;
  if (editingMaterialId !== null) {
    res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/material/${editingMaterialId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } else {
    res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/material`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  if (res.ok) {
    closeModal();
    await loadDetail();
  } else {
    const err = await res.json();
    alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen"));
  }
});

async function deleteMaterial(id) {
  if (!confirm("Diesen Material-Eintrag löschen?")) return;
  const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/material/${id}`, { method: "DELETE" });
  if (res.ok) {
    await loadDetail();
  } else {
    const err = await res.json();
    alert("Error: " + (err.detail || "Failed to delete material"));
  }
}

// ── Freitext price auto-calculation ──────────────────────────

function recalcFreitextTotal() {
  const menge = parseFloat(document.getElementById("field-mat-menge").value);
  const unitPrice = parseFloat(document.getElementById("field-mat-unit-price").value);
  if (!isNaN(menge) && menge > 0 && !isNaN(unitPrice) && unitPrice >= 0) {
    document.getElementById("field-mat-total-price").value = parseFloat((menge * unitPrice).toFixed(4));
  }
}

function recalcFreitextUnitPrice() {
  const menge = parseFloat(document.getElementById("field-mat-menge").value);
  const total = parseFloat(document.getElementById("field-mat-total-price").value);
  if (!isNaN(menge) && menge > 0 && !isNaN(total) && total >= 0) {
    document.getElementById("field-mat-unit-price").value = parseFloat((total / menge).toFixed(6));
  }
}

document.getElementById("field-mat-menge").addEventListener("input", recalcFreitextTotal);
document.getElementById("field-mat-unit-price").addEventListener("input", recalcFreitextTotal);
document.getElementById("field-mat-total-price").addEventListener("input", recalcFreitextUnitPrice);

document.getElementById("add-material-btn").addEventListener("click", openAddMaterial);
document.getElementById("add-aufrunden-btn").addEventListener("click", openAufrundenModal);
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("cancel-mat-btn").addEventListener("click", closeModal);
document.getElementById("modal-overlay").addEventListener("click", closeModal);

// ── Spende Modal ──────────────────────────────────────────────

function openSpendeModal() {
  document.getElementById("field-spende-name").value = "Spende";
  document.getElementById("field-spende-amount").value = "";
  document.getElementById("aufrunden-group").style.display = "none";
  document.getElementById("direct-amount-group").style.display = "block";
  document.getElementById("spende-modal").classList.remove("hidden");
  document.getElementById("field-spende-amount").focus();
}

function openAufrundenModal() {
  document.getElementById("field-spende-name").value = "Spende";
  document.getElementById("field-spende-amount").value = "";
  document.getElementById("aufrunden-group").style.display = "block";
  document.getElementById("direct-amount-group").style.display = "none";
  document.getElementById("spende-modal").classList.remove("hidden");
  const currentTotal = getTotal();
  document.getElementById("current-total").textContent = currentTotal.toFixed(2);
  const nextRound = Math.ceil(currentTotal);
  document.getElementById("field-spende-aufrunden-amount").value = nextRound.toFixed(2);
  updateAufrundenDiff();
  document.getElementById("field-spende-aufrunden-amount").focus();
}

function closeSpendeModal() {
  document.getElementById("spende-modal").classList.add("hidden");
}

document.getElementById("field-spende-aufrunden-amount").addEventListener("input", updateAufrundenDiff);

function updateAufrundenDiff() {
  const target = parseFloat(document.getElementById("field-spende-aufrunden-amount").value);
  const currentTotal = getTotal();
  if (!isNaN(target) && target > currentTotal) {
    const diff = target - currentTotal;
    document.getElementById("aufrunden-diff").textContent = diff.toFixed(2);
  } else {
    document.getElementById("aufrunden-diff").textContent = "–";
  }
}

document.getElementById("spende-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("field-spende-name").value.trim() || "Spende";
  const isAufrundenMode = document.getElementById("aufrunden-group").style.display !== "none";
  let amount;

  if (isAufrundenMode) {
    const target = parseFloat(document.getElementById("field-spende-aufrunden-amount").value);
    const currentTotal = getTotal();
    if (isNaN(target) || target <= currentTotal) {
      alert("Bitte einen Betrag eingeben, der höher als die aktuelle Summe ist.");
      return;
    }
    amount = target - currentTotal;
  } else {
    amount = parseFloat(document.getElementById("field-spende-amount").value);
    if (isNaN(amount) || amount <= 0) {
      alert("Bitte gültigen Betrag eingeben.");
      return;
    }
  }

  const body = { name, calculated_price: parseFloat(amount.toFixed(2)), tax_rate: 0, is_spende: true };
  const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/material`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeSpendeModal();
    await loadDetail();
  } else {
    const err = await res.json();
    alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen"));
  }
});

document.getElementById("spende-modal-close").addEventListener("click", closeSpendeModal);
document.getElementById("spende-cancel").addEventListener("click", closeSpendeModal);
document.getElementById("spende-overlay").addEventListener("click", closeSpendeModal);

// Wait for katalog to load before rendering materials
loadKatalog().then(() => {
  loadLogo()
    .then(() => {
      return loadPaymentConfig();
    })
    .then(() => loadDetail());
});

// ── Payment UI ────────────────────────────────────────────────

function getTotal() {
  const mats = currentData && currentData.material ? currentData.material : [];
  return mats.reduce((sum, m) => sum + (m.calculated_price != null ? m.calculated_price : 0), 0);
}

function getRemaining() {
  if (currentData && currentData.remaining_amount != null) return currentData.remaining_amount;
  return getTotal();
}

function fmtEur(val) {
  return val.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
}

// ── Gutschein (Gift Card) ─────────────────────────────────────────────────────

let _pendingGutschein = null; // { id, last_chars, balance }

function toggleGutscheinForm() {
  const container = document.getElementById("gutschein-form-container");
  const btn = document.getElementById("gutschein-toggle-btn");
  const hidden = container.classList.contains("hidden");
  container.classList.toggle("hidden", !hidden);
  btn.textContent = hidden ? "🎁 Gutschein schließen" : "🎁 Gutschein einlösen";
}

async function lookupGutschein() {
  const raw = (document.getElementById("gutschein-last-chars").value || "").trim().toUpperCase();
  const errEl = document.getElementById("gutschein-lookup-error");
  const resultEl = document.getElementById("gutschein-lookup-result");
  errEl.classList.add("hidden");
  resultEl.classList.add("hidden");
  _pendingGutschein = null;

  if (!raw) {
    errEl.textContent = "Bitte Zeichen eingeben.";
    errEl.classList.remove("hidden");
    return;
  }

  try {
    const res = await fetch(`/api/shopify/gift-cards/lookup?last_chars=${encodeURIComponent(raw)}`);
    if (!res.ok) {
      const e = await res.json();
      throw new Error(e.detail || "Fehler");
    }
    const cards = await res.json();
    if (!cards.length) {
      errEl.textContent = "Kein aktiver Gutschein mit diesen Zeichen gefunden.";
      errEl.classList.remove("hidden");
      return;
    }

    const list = document.getElementById("gutschein-card-list");
    list.innerHTML = "";
    if (cards.length > 1) {
      const hdr = document.createElement("p");
      hdr.style.cssText = "font-size:0.82rem;color:var(--text-secondary);margin:0 0 8px 0;";
      hdr.textContent = `${cards.length} Gutscheine gefunden – bitte den richtigen auswählen:`;
      list.appendChild(hdr);
    }
    cards.forEach((card) => {
      const row = document.createElement("div");
      row.style.cssText =
        "display:flex;justify-content:space-between;align-items:center;padding:9px 12px;border-radius:6px;border:1px solid var(--border);margin-bottom:6px;cursor:pointer;background:var(--bg);";
      row.dataset.cardId = card.id;
      const _nameTag = card.customer_name
        ? `<span style="font-size:0.85rem;">${card.customer_name}</span>`
        : `<span style="font-size:0.82rem;color:var(--text-secondary);">kein Kunde</span>`;
      row.innerHTML = `<span style="font-family:monospace;font-weight:600;">…${card.last_chars}</span>${_nameTag}<span style="font-size:0.9rem;">Guthaben: <strong>${fmtEur(card.balance)}</strong></span>`;
      row.addEventListener("click", () => _selectGutscheinCard(card, row));
      list.appendChild(row);
    });
    document.getElementById("gutschein-apply-row").classList.add("hidden");
    resultEl.classList.remove("hidden");

    if (cards.length === 1) {
      _selectGutscheinCard(cards[0], list.querySelector("div[data-card-id]"));
    }
  } catch (err) {
    errEl.textContent = err.message || "Suche fehlgeschlagen.";
    errEl.classList.remove("hidden");
  }
}

function _selectGutscheinCard(card, rowEl) {
  document.querySelectorAll("#gutschein-card-list div[data-card-id]").forEach((el) => {
    el.style.background = "var(--bg)";
    el.style.borderColor = "var(--border)";
  });
  rowEl.style.background = "var(--bg-secondary)";
  rowEl.style.borderColor = "var(--primary, #4a9eff)";
  _pendingGutschein = card;
  const capped = Math.min(card.balance, getRemaining());
  const amtInput = document.getElementById("gutschein-amount-input");
  amtInput.value = capped.toFixed(2);
  amtInput.max = capped.toFixed(2);
  document.getElementById("gutschein-apply-row").classList.remove("hidden");
}

async function applyGutschein() {
  if (!_pendingGutschein) return;
  const amount = parseFloat(document.getElementById("gutschein-amount-input").value);
  if (!amount || amount <= 0) {
    alert("Bitte einen gültigen Betrag eingeben.");
    return;
  }
  const btn = document.getElementById("gutschein-apply-btn");
  btn.disabled = true;
  btn.textContent = "…";
  try {
    const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/apply-gutschein`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        shopify_gift_card_id: _pendingGutschein.id,
        last_chars: _pendingGutschein.last_chars,
        amount,
        note: "",
      }),
    });
    if (res.ok) {
      currentData = await res.json();
      renderInfo();
      renderMaterial();
      document.getElementById("gutschein-form-container").classList.add("hidden");
      document.getElementById("gutschein-toggle-btn").textContent = "🎁 Gutschein einlösen";
      document.getElementById("gutschein-last-chars").value = "";
      _pendingGutschein = null;
    } else {
      const err = await res.json();
      alert("Fehler: " + (err.detail || "Unbekannter Fehler"));
    }
  } finally {
    btn.disabled = false;
    btn.textContent = "Einlösen";
  }
}

async function removeGutschein(gutscheinId) {
  if (!confirm("Gutschein-Gutschrift stornieren und Betrag zurückbuchen?")) return;
  const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/gutschein/${gutscheinId}`, { method: "DELETE" });
  if (res.ok) {
    currentData = (await res.json) ? await res.json() : currentData;
    // Reload full data
    const r2 = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}`);
    if (r2.ok) currentData = await r2.json();
    renderInfo();
    renderMaterial();
  } else {
    const err = await res.json();
    alert("Fehler beim Stornieren: " + (err.detail || "Unbekannter Fehler"));
  }
}

function renderGutscheinCredits(locked) {
  const credits = (currentData && currentData.gutschein_credits) || [];
  const totalCredited = (currentData && currentData.total_credited) || 0;
  const remaining = currentData && currentData.remaining_amount != null ? currentData.remaining_amount : null;

  const section = document.getElementById("gutschein-credits-section");
  const gutscheinSection = document.getElementById("gutschein-section");

  if (credits.length > 0) {
    section.classList.remove("hidden");
    const list = document.getElementById("gutschein-credits-list");
    list.innerHTML = credits
      .map(
        (c) => `
            <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;background:var(--bg-secondary);border-radius:6px;border:1px solid var(--border);">
                <span style="font-size:0.9rem;">🎁 Gutschein …${esc(c.last_chars)} — <strong style="color:var(--success);">-${fmtEur(c.amount_debited)}</strong></span>
                ${!locked ? `<button class="btn btn-sm btn-danger" onclick="removeGutschein(${c.id})" style="padding:2px 8px;font-size:0.78rem;">✕</button>` : ""}
            </div>`,
      )
      .join("");
    if (remaining !== null) {
      document.getElementById("remaining-amount-display").textContent = fmtEur(remaining);
      document.getElementById("remaining-amount-row").style.display = remaining <= 0 ? "none" : "";
    }
  } else {
    section.classList.add("hidden");
  }

  if (!locked) {
    gutscheinSection.classList.remove("hidden");
  } else {
    gutscheinSection.classList.add("hidden");
  }
}

function renderPaymentSection(total, hasAnyPrice) {
  const section = document.getElementById("payment-section");
  const d = currentData;
  if (!hasAnyPrice || total <= 0) {
    section.classList.add("hidden");
    return;
  }
  section.classList.remove("hidden");

  const locked = !!d.payment_method;
  const banner = document.getElementById("payment-locked-banner");
  const buttons = document.getElementById("payment-buttons");

  renderGutscheinCredits(locked);

  if (locked) {
    buttons.classList.add("hidden");
    banner.classList.remove("hidden");
    const methodLabels = {
      bar: "Bar bezahlt",
      karte: "Per Karte bezahlt",
      wero: "Per Wero bezahlt",
      gutschein: "Per Gutschein bezahlt",
      bank_transfer: "Per \u00dcberweisung bezahlt",
    };
    const label = methodLabels[d.payment_method] || "Bezahlt";
    const paidDate = d.paid_at ? new Date(d.paid_at).toLocaleString("de-DE") : "";
    document.getElementById("payment-locked-text").textContent = `${label}${paidDate ? " \u2013 " + paidDate : ""}`;
    const txnEl = document.getElementById("payment-locked-txn");
    if (d.payment_transaction_id) {
      txnEl.textContent = `TXN: ${d.payment_transaction_id}`;
      txnEl.style.display = "";
    } else {
      txnEl.style.display = "none";
    }
    const notesEl = document.getElementById("payment-locked-notes");
    if (d.payment_notes) {
      notesEl.textContent = d.payment_notes;
      notesEl.style.display = "";
    } else {
      notesEl.style.display = "none";
    }
    document.querySelectorAll("#material-body .btn-danger, #material-body .btn-secondary").forEach((btn) => {
      btn.disabled = true;
      btn.style.opacity = "0.4";
      btn.style.cursor = "not-allowed";
    });
  } else {
    const remaining = getRemaining();
    if (remaining <= 0.005 && (d.gutschein_credits || []).length > 0) {
      buttons.classList.add("hidden");
    } else {
      buttons.classList.remove("hidden");
      document.getElementById("pay-now-amount").textContent = fmtEur(remaining);
    }
    banner.classList.add("hidden");
  }
}

// ── Unified Payment Modal ────────────────────────────────────────────────────

function _buildMethodSwitcher(defaultMethod) {
  const switcher = document.getElementById("pay-method-switcher");
  switcher.innerHTML = "";
  const methods = [];
  if (paymentConfig.bank_transfer_configured) methods.push({ id: "bank", label: "🏦 Banküberweisung" });
  if (paymentConfig.sumup_configured) methods.push({ id: "sumup", label: "💳 EC-/Kreditkarte" });
  methods.push({ id: "bar", label: "💵 Barzahlung" });
  methods.forEach(({ id, label }) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.method = id;
    btn.className = "btn btn-secondary pay-method-btn";
    btn.style.cssText = "flex:1;min-width:120px;font-size:0.82rem;padding:7px 10px;";
    btn.textContent = label;
    btn.onclick = () => switchPayMethod(id);
    switcher.appendChild(btn);
  });
  _highlightMethodBtn(defaultMethod);
}

function _highlightMethodBtn(method) {
  document.querySelectorAll(".pay-method-btn").forEach((b) => {
    const active = b.dataset.method === method;
    b.style.background = active ? "var(--primary,#3b82f6)" : "";
    b.style.color = active ? "#fff" : "";
    b.style.borderColor = active ? "var(--primary,#3b82f6)" : "";
  });
}

function switchPayMethod(method) {
  document.querySelectorAll(".pay-panel-view").forEach((p) => p.classList.add("hidden"));
  const panel = document.getElementById("panel-" + method);
  if (panel) panel.classList.remove("hidden");
  _highlightMethodBtn(method);
  if (method === "bank") loadBankPanel();
  if (method === "bar") {
    document.getElementById("bar-total-display").textContent = fmtEur(getRemaining());
    document.getElementById("bar-notes-input").value = "";
  }
}

async function openPayModal() {
  const remaining = getRemaining();
  document.getElementById("pay-modal-amount").textContent = fmtEur(remaining);
  document.getElementById("pay-modal").classList.remove("hidden");
  const defaultMethod = paymentConfig.bank_transfer_configured ? "bank"
    : paymentConfig.sumup_configured ? "sumup" : "bar";
  _buildMethodSwitcher(defaultMethod);
  switchPayMethod(defaultMethod);
}

function closePayModal() {
  document.getElementById("pay-modal").classList.add("hidden");
  document.getElementById("bank-qr-container-inline").innerHTML = "";
  document.getElementById("bank-qr-section-inline").classList.add("hidden");
  document.getElementById("bank-spinner-inline").style.display = "";
  document.getElementById("bank-actions-inline").style.display = "none";
  const bc = document.getElementById("bank-confirm-btn-inline");
  bc.disabled = false; bc.textContent = "✓ Bezahlt";
  const barc = document.getElementById("bar-confirm-btn");
  barc.disabled = false; barc.textContent = "Bezahlt ✓";
}

document.getElementById("pay-modal-close").addEventListener("click", closePayModal);
document.getElementById("pay-modal-overlay").addEventListener("click", closePayModal);

async function confirmBarPayment() {
  const btn = document.getElementById("bar-confirm-btn");
  btn.disabled = true;
  btn.textContent = "…";
  const notes = (document.getElementById("bar-notes-input").value || "").trim();
  const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/bar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes }),
  });
  btn.disabled = false;
  btn.textContent = "Bezahlt ✓";
  if (res.ok) {
    currentData = await res.json();
    renderInfo();
    renderMaterial();
    closePayModal();
  } else {
    const err = await res.json();
    alert("Fehler: " + (err.detail || "Unbekannter Fehler"));
  }
}

// Reset payment modal
function openResetPaymentModal() {
  document.getElementById("reset-payment-modal").classList.remove("hidden");
}
function closeResetPaymentModal() {
  document.getElementById("reset-payment-modal").classList.add("hidden");
  const btn = document.getElementById("reset-payment-confirm");
  btn.disabled = false;
  btn.textContent = "Ja, Zahlung zurücksetzen";
}
async function confirmResetPayment() {
  const btn = document.getElementById("reset-payment-confirm");
  btn.disabled = true;
  btn.textContent = "…";
  const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay`, { method: "DELETE" });
  if (res.ok) {
    currentData = await res.json();
    renderInfo();
    renderMaterial();
    closeResetPaymentModal();
  } else {
    const err = await res.json();
    btn.disabled = false;
    btn.textContent = "Ja, Zahlung zurücksetzen";
    alert("Fehler: " + (err.detail || "Unbekannter Fehler"));
  }
}
document.getElementById("reset-payment-close").addEventListener("click", closeResetPaymentModal);
document.getElementById("reset-payment-cancel").addEventListener("click", closeResetPaymentModal);
document.getElementById("reset-payment-overlay").addEventListener("click", closeResetPaymentModal);

// Karte payment state
let kartePollAbort = null;
let karteCurrentTxnId = null;

// Karte
async function doKartePayment() {
  const modal = document.getElementById("karte-modal");
  const statusText = document.getElementById("karte-status-text");
  const actions = document.getElementById("karte-actions");
  const body = document.getElementById("karte-body");
  const spinner = body.querySelector(".karte-spinner");

  // Reset state
  kartePollAbort = new AbortController();
  karteCurrentTxnId = null;

  statusText.textContent = "Zahlung wird ans Terminal gesendet…";
  statusText.style.color = "";
  spinner.style.display = "";
  actions.style.display = "none";
  modal.classList.remove("hidden");

  // Phase 1: initiate checkout
  let initData;
  try {
    const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/karte`, {
      method: "POST",
      signal: kartePollAbort.signal,
    });
    if (!res.ok) {
      const err = await res.json();
      statusText.textContent = "Fehler: " + (err.detail || "Unbekannter Fehler");
      statusText.style.color = "var(--danger)";
      spinner.style.display = "none";
      actions.style.display = "";
      return;
    }
    initData = await res.json();
    karteCurrentTxnId = initData.client_transaction_id;
  } catch (e) {
    if (e.name === "AbortError") {
      statusText.textContent = "Zahlung abgebrochen.";
      statusText.style.color = "var(--warning)";
    } else {
      statusText.textContent = "Netzwerkfehler beim Senden ans Terminal.";
      statusText.style.color = "var(--danger)";
    }
    spinner.style.display = "none";
    actions.style.display = "";
    return;
  }

  // Phase 2: mock mode – lock immediately without polling
  if (initData.mock) {
    spinner.style.display = "none";
    statusText.textContent = "✓ Mock-Modus: Zahlung simuliert und gespeichert.";
    statusText.style.color = "var(--success)";
    const confirmRes = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/karte/confirm-mock`, { method: "POST" });
    if (confirmRes.ok) {
      currentData = await confirmRes.json();
      renderInfo();
      renderMaterial();
    }
    actions.style.display = "";
    return;
  }

  // Phase 2b: Payment Switch mode – QR code for cross-device SumUp app
  if (initData.mode === "payment_switch") {
    spinner.style.display = "none";
    statusText.textContent = `Betrag: ${initData.amount} € – QR-Code mit SumUp App scannen`;
    statusText.style.color = "";

    // Inject QR code + buttons into body
    let switchDiv = document.getElementById("karte-switch-actions");
    if (!switchDiv) {
      switchDiv = document.createElement("div");
      switchDiv.id = "karte-switch-actions";
      switchDiv.style.cssText = "display:flex;flex-direction:column;gap:0.75rem;margin-top:1rem;align-items:center;";
      body.appendChild(switchDiv);
    }
    switchDiv.innerHTML = `
            <div id="karte-qr-canvas" style="background:#fff;padding:12px;border-radius:8px;display:inline-block;"></div>
            <p style="font-size:0.85rem;color:var(--text-secondary);text-align:center;margin:0;">
                SumUp App auf dem Handy öffnen → QR-Code scannen
            </p>
            <a href="${initData.payment_url}" class="btn btn-payment btn-payment-karte" style="text-align:center;text-decoration:none;width:100%;" target="_blank">
                📲 SumUp App öffnen (gleiches Gerät)
            </a>
            <p style="font-size:0.82rem;color:var(--text-secondary);text-align:center;margin:0;">
                ⏳ Warte auf Zahlungsbestätigung von SumUp…
            </p>`;

    // Generate QR code
    if (typeof qrcode !== "undefined") {
      makeQR(document.getElementById("karte-qr-canvas"), initData.payment_url, 200, "M");
    }

    actions.style.display = "";

    // Poll SumUp in the background; auto-confirm once payment is detected
    const switchTxnId = initData.client_transaction_id;
    const SWITCH_POLL_MS = 5000;
    const pollSwitch = async () => {
      if (kartePollAbort.signal.aborted) return;
      try {
        const r = await fetch(
          `/api/laufzettel/${LAUFZETTEL_ID}/pay/karte/status?client_transaction_id=${encodeURIComponent(switchTxnId)}`,
          { signal: kartePollAbort.signal },
        );
        const pollData = await r.json();
        if (pollData.status === "SUCCESSFUL") {
          if (pollData.laufzettel) {
            currentData = pollData.laufzettel;
            renderInfo();
            renderMaterial();
          }
          if (switchDiv) switchDiv.remove();
          statusText.textContent = "✓ Zahlung erfolgreich bestätigt!";
          statusText.style.color = "var(--success)";
        } else if (pollData.status === "TIMEOUT" || pollData.status === "NOT_FOUND") {
          statusText.textContent = "⚠️ Zahlung nicht bestätigt – bitte im SumUp-Dashboard prüfen.";
          statusText.style.color = "var(--warning, #f59e0b)";
        } else {
          setTimeout(pollSwitch, SWITCH_POLL_MS);
        }
      } catch (e) {
        if (e.name !== "AbortError") setTimeout(pollSwitch, SWITCH_POLL_MS);
      }
    };
    setTimeout(pollSwitch, SWITCH_POLL_MS);
    return;
  }

  // Phase 3: Solo Cloud API mode – poll for SUCCESSFUL / CANCELLED / FAILED / TIMEOUT
  const txnId = initData.client_transaction_id;
  statusText.textContent = "Warte auf Bestätigung am Terminal…";

  const POLL_INTERVAL_MS = 3000;
  const POLL_TIMEOUT_MS = 60000; // 1 minute max (backend timeout)
  const started = Date.now();

  const poll = async () => {
    // Check if aborted
    if (kartePollAbort.signal.aborted) {
      return;
    }

    if (Date.now() - started > POLL_TIMEOUT_MS) {
      spinner.style.display = "none";
      statusText.textContent = "Timeout – keine Antwort vom Terminal erhalten.";
      statusText.style.color = "var(--warning)";
      actions.style.display = "";
      // Notify backend to cancel
      try {
        await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/karte?client_transaction_id=${encodeURIComponent(txnId)}`, {
          method: "DELETE",
        });
      } catch (_) {}
      return;
    }

    let pollData;
    try {
      const r = await fetch(
        `/api/laufzettel/${LAUFZETTEL_ID}/pay/karte/status?client_transaction_id=${encodeURIComponent(txnId)}`,
        { signal: kartePollAbort.signal },
      );
      pollData = await r.json();
    } catch (e) {
      if (e.name === "AbortError") {
        return; // Stopped by user
      }
      setTimeout(poll, POLL_INTERVAL_MS);
      return;
    }

    if (pollData.status === "SUCCESSFUL") {
      spinner.style.display = "none";
      statusText.textContent = "✓ Zahlung erfolgreich bestätigt!";
      statusText.style.color = "var(--success)";
      if (pollData.laufzettel) {
        currentData = pollData.laufzettel;
        renderInfo();
        renderMaterial();
      }
      actions.style.display = "";
    } else if (pollData.status === "CANCELLED" || pollData.status === "FAILED" || pollData.status === "TIMEOUT") {
      spinner.style.display = "none";
      if (pollData.status === "TIMEOUT") {
        statusText.textContent = "Timeout – keine Antwort vom Terminal erhalten.";
        statusText.style.color = "var(--warning)";
      } else {
        statusText.textContent = pollData.status === "CANCELLED" ? "Zahlung abgebrochen." : "Zahlung fehlgeschlagen.";
        statusText.style.color = "var(--danger)";
      }
      actions.style.display = "";
    } else {
      // Still PENDING – keep polling
      setTimeout(poll, POLL_INTERVAL_MS);
    }
  };

  setTimeout(poll, POLL_INTERVAL_MS);
}

function closeKarteModal() {
  const modal = document.getElementById("karte-modal");
  const statusText = document.getElementById("karte-status-text");

  // Abort any ongoing fetch/polling
  if (kartePollAbort) {
    kartePollAbort.abort();
    kartePollAbort = null;
  }

  // Notify backend to cancel pending payment
  if (karteCurrentTxnId) {
    fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/karte?client_transaction_id=${encodeURIComponent(karteCurrentTxnId)}`, {
      method: "DELETE",
    }).catch(() => {});
    karteCurrentTxnId = null;
  }

  modal.classList.add("hidden");
  statusText.style.color = "";
  const switchDiv = document.getElementById("karte-switch-actions");
  if (switchDiv) switchDiv.remove();
}
document.getElementById("karte-modal-close").addEventListener("click", closeKarteModal);
document.getElementById("karte-close-btn").addEventListener("click", closeKarteModal);

// Hosted checkout (customer-facing Apple/Google Pay QR)
let checkoutCurrentId = null;
let checkoutPollAbort = null;

async function doCheckoutPayment() {
  const modal = document.getElementById("checkout-modal");
  const statusText = document.getElementById("checkout-status-text");
  const actions = document.getElementById("checkout-actions");
  const body = document.getElementById("checkout-body");
  const spinner = body.querySelector(".karte-spinner");

  checkoutPollAbort = new AbortController();
  checkoutCurrentId = null;

  statusText.textContent = "Zahlungslink wird erstellt…";
  statusText.style.color = "";
  spinner.style.display = "";
  actions.style.display = "none";
  modal.classList.remove("hidden");

  const oldArea = document.getElementById("checkout-qr-area");
  if (oldArea) oldArea.remove();

  let initData;
  try {
    const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/checkout`, {
      method: "POST",
      signal: checkoutPollAbort.signal,
    });
    if (!res.ok) {
      const err = await res.json();
      statusText.textContent = "Fehler: " + (err.detail || "Unbekannter Fehler");
      statusText.style.color = "var(--danger)";
      spinner.style.display = "none";
      actions.style.display = "";
      return;
    }
    initData = await res.json();
    checkoutCurrentId = initData.checkout_id;
  } catch (e) {
    if (e.name === "AbortError") return;
    statusText.textContent = "Netzwerkfehler beim Erstellen des Zahlungslinks.";
    statusText.style.color = "var(--danger)";
    spinner.style.display = "none";
    actions.style.display = "";
    return;
  }

  spinner.style.display = "none";
  statusText.textContent = `Betrag: ${initData.amount} € – QR-Code mit dem Handy scannen`;

  const qrArea = document.createElement("div");
  qrArea.id = "checkout-qr-area";
  qrArea.style.cssText = "display:flex;flex-direction:column;gap:0.75rem;margin-top:1rem;align-items:center;";
  qrArea.innerHTML = `
        <div id="checkout-qr-canvas" style="background:#fff;padding:12px;border-radius:8px;display:inline-block;"></div>
        <p style="font-size:0.85rem;color:var(--text-secondary);text-align:center;margin:0;">
            QR-Code scannen → im Browser zahlen (Apple Pay, Google Pay, Karte)
        </p>
        <a href="${initData.checkout_url}" class="btn btn-payment btn-payment-checkout" style="text-align:center;text-decoration:none;width:100%;" target="_blank">
            🔗 Link öffnen (gleiches Gerät)
        </a>
        <p id="checkout-poll-status" style="font-size:0.85rem;color:var(--text-secondary);text-align:center;margin:0;">
            Warte auf Zahlung…
        </p>`;
  body.appendChild(qrArea);

  if (typeof qrcode !== "undefined") {
    makeQR(document.getElementById("checkout-qr-canvas"), initData.checkout_url, 200, "M");
  }

  actions.style.display = "";

  const POLL_INTERVAL_MS = 5000;
  const poll = async () => {
    if (checkoutPollAbort.signal.aborted) return;
    try {
      const r = await fetch(
        `/api/laufzettel/${LAUFZETTEL_ID}/pay/checkout/status?checkout_id=${encodeURIComponent(checkoutCurrentId)}`,
        { signal: checkoutPollAbort.signal },
      );
      const data = await r.json();
      const pollStatus = document.getElementById("checkout-poll-status");
      if (data.status === "PAID") {
        statusText.textContent = "✓ Zahlung erfolgreich!";
        statusText.style.color = "var(--success)";
        if (pollStatus) pollStatus.remove();
        if (data.laufzettel) {
          currentData = data.laufzettel;
          renderInfo();
          renderMaterial();
        }
      } else if (data.status === "FAILED" || data.status === "EXPIRED") {
        statusText.textContent = data.status === "EXPIRED" ? "Zahlungslink abgelaufen." : "Zahlung fehlgeschlagen.";
        statusText.style.color = "var(--danger)";
        if (pollStatus) pollStatus.textContent = "";
      } else {
        setTimeout(poll, POLL_INTERVAL_MS);
      }
    } catch (e) {
      if (e.name !== "AbortError") setTimeout(poll, POLL_INTERVAL_MS);
    }
  };
  setTimeout(poll, POLL_INTERVAL_MS);
}

function closeCheckoutModal() {
  if (checkoutPollAbort) {
    checkoutPollAbort.abort();
    checkoutPollAbort = null;
  }
  if (checkoutCurrentId) {
    fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/checkout?checkout_id=${encodeURIComponent(checkoutCurrentId)}`, {
      method: "DELETE",
    }).catch(() => {});
    checkoutCurrentId = null;
  }
  document.getElementById("checkout-modal").classList.add("hidden");
  const qrArea = document.getElementById("checkout-qr-area");
  if (qrArea) qrArea.remove();
}
document.getElementById("checkout-modal-close").addEventListener("click", closeCheckoutModal);
document.getElementById("checkout-close-btn").addEventListener("click", closeCheckoutModal);
document.getElementById("checkout-modal-overlay").addEventListener("click", closeCheckoutModal);

// ── Wero Payment ────────────────────────────────────────────────────────────

let weroPollAbort = null;
let weroCurrentCheckoutId = null;

async function doWeroPayment() {
  const modal = document.getElementById("wero-modal");
  const statusText = document.getElementById("wero-status-text");
  const actions = document.getElementById("wero-actions");
  const body = document.getElementById("wero-body");
  const spinner = body.querySelector(".karte-spinner");
  const qrSection = document.getElementById("wero-qr-section");

  weroPollAbort = new AbortController();
  weroCurrentCheckoutId = null;

  // Reset modal state
  statusText.textContent = "Zahlungslink wird erstellt…";
  statusText.style.color = "";
  spinner.style.display = "";
  actions.style.display = "none";
  qrSection.classList.add("hidden");
  const oldQr = document.getElementById("wero-qr-container");
  oldQr.innerHTML = "";
  modal.classList.remove("hidden");

  let initData;
  try {
    const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/wero`, {
      method: "POST",
      signal: weroPollAbort.signal,
    });
    if (!res.ok) {
      const err = await res.json();
      statusText.textContent = "Fehler: " + (err.detail || "Unbekannter Fehler");
      statusText.style.color = "var(--danger)";
      spinner.style.display = "none";
      actions.style.display = "";
      return;
    }
    initData = await res.json();
    weroCurrentCheckoutId = initData.checkout_id;
  } catch (e) {
    if (e.name === "AbortError") {
      statusText.textContent = "Zahlung abgebrochen.";
      statusText.style.color = "var(--warning)";
    } else {
      statusText.textContent = "Netzwerkfehler beim Erstellen des Wero-Links.";
      statusText.style.color = "var(--danger)";
    }
    spinner.style.display = "none";
    actions.style.display = "";
    return;
  }

  spinner.style.display = "none";
  statusText.textContent = "Scanne den QR-Code mit deiner Banking-App:";

  // Show QR code section
  document.getElementById("wero-amount-display").textContent = initData.amount + " €";
  qrSection.classList.remove("hidden");

  // Generate QR code for Wero payment URL
  if (typeof qrcode !== "undefined") {
    makeQR(document.getElementById("wero-qr-container"), initData.payment_url, 200, "M");
  }

  actions.style.display = "";

  // Poll for payment status
  const POLL_INTERVAL_MS = 3000;
  const poll = async () => {
    if (weroPollAbort.signal.aborted) return;
    try {
      const r = await fetch(
        `/api/laufzettel/${LAUFZETTEL_ID}/pay/wero/status?checkout_id=${encodeURIComponent(weroCurrentCheckoutId)}`,
        { signal: weroPollAbort.signal },
      );
      const pollData = await r.json();

      if (pollData.status === "PAID") {
        statusText.textContent = "✓ Zahlung erfolgreich bestätigt!";
        statusText.style.color = "var(--success)";
        if (pollData.laufzettel) {
          currentData = pollData.laufzettel;
          renderInfo();
          renderMaterial();
        }
        // Auto-close after success
        setTimeout(() => closeWeroModal(), 1500);
      } else if (pollData.status === "TIMEOUT" || pollData.status === "NOT_FOUND") {
        statusText.textContent = "⚠️ Zahlung nicht bestätigt – bitte erneut versuchen.";
        statusText.style.color = "var(--warning, #f59e0b)";
      } else {
        setTimeout(poll, POLL_INTERVAL_MS);
      }
    } catch (e) {
      if (e.name !== "AbortError") setTimeout(poll, POLL_INTERVAL_MS);
    }
  };
  setTimeout(poll, POLL_INTERVAL_MS);
}

async function confirmWeroPayment() {
  if (!weroCurrentCheckoutId) return;
  const btn = document.getElementById("wero-confirm-btn");
  btn.disabled = true;
  btn.textContent = "…";

  try {
    const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/wero/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checkout_id: weroCurrentCheckoutId }),
    });
    if (res.ok) {
      currentData = await res.json();
      renderInfo();
      renderMaterial();
      closeWeroModal();
    } else {
      const err = await res.json();
      btn.disabled = false;
      btn.textContent = "✓ Bezahlt";
      alert("Fehler: " + (err.detail || "Unbekannter Fehler"));
    }
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "✓ Bezahlt";
    alert("Netzwerkfehler");
  }
}

function closeWeroModal() {
  const modal = document.getElementById("wero-modal");

  if (weroPollAbort) {
    weroPollAbort.abort();
    weroPollAbort = null;
  }

  if (weroCurrentCheckoutId) {
    fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/wero?checkout_id=${encodeURIComponent(weroCurrentCheckoutId)}`, {
      method: "DELETE",
    }).catch(() => {});
    weroCurrentCheckoutId = null;
  }

  modal.classList.add("hidden");
  document.getElementById("wero-status-text").style.color = "";
  document.getElementById("wero-qr-section").classList.add("hidden");
  document.getElementById("wero-qr-container").innerHTML = "";
  const btn = document.getElementById("wero-confirm-btn");
  btn.disabled = false;
  btn.textContent = "✓ Bezahlt";
}

document.getElementById("wero-modal-close").addEventListener("click", closeWeroModal);
document.getElementById("wero-cancel-btn").addEventListener("click", closeWeroModal);
document.getElementById("wero-modal-overlay").addEventListener("click", closeWeroModal);

// ── Bank Transfer / EPC QR ─────────────────────────────────────────────────────────

/**
 * Build the EPC QR string per GS1 / European Payments Council spec (Version 002).
 * Banking apps (Sparkasse, ING, DKB, N26, Commerzbank, …) parse this natively.
 */
function buildEpcQrString({ account_name, bic, iban, amount, reference }) {
  const amountStr = "EUR" + Number(amount).toFixed(2);
  return [
    "BCD",          // Service Tag
    "002",          // Version
    "1",            // Encoding: UTF-8
    "SCT",          // SEPA Credit Transfer
    bic,
    account_name,
    iban,
    amountStr,
    "",             // Purpose (empty)
    reference,      // Remittance info (structured)
    "",             // Remittance info (unstructured) – leave empty
    "",             // Beneficiary info
  ].join("\n");
}

async function loadBankPanel() {
  const spinner = document.getElementById("bank-spinner-inline");
  const statusText = document.getElementById("bank-status-text-inline");
  const qrSection = document.getElementById("bank-qr-section-inline");
  const actions = document.getElementById("bank-actions-inline");

  spinner.style.display = "";
  statusText.textContent = "Daten werden geladen\u2026";
  statusText.style.color = "";
  qrSection.classList.add("hidden");
  actions.style.display = "none";
  document.getElementById("bank-qr-container-inline").innerHTML = "";

  let data;
  try {
    const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/bank-transfer`);
    if (!res.ok) {
      const err = await res.json();
      statusText.textContent = "Fehler: " + (err.detail || "Unbekannter Fehler");
      statusText.style.color = "var(--danger)";
      spinner.style.display = "none";
      return;
    }
    data = await res.json();
  } catch (e) {
    statusText.textContent = "Netzwerkfehler.";
    statusText.style.color = "var(--danger)";
    spinner.style.display = "none";
    return;
  }

  spinner.style.display = "none";
  document.getElementById("bank-detail-name-inline").textContent = data.account_name;
  document.getElementById("bank-detail-iban-inline").textContent = data.iban;
  document.getElementById("bank-detail-bic-inline").textContent = data.bic;
  document.getElementById("bank-detail-amount-inline").textContent = fmtEur(data.amount);
  document.getElementById("bank-detail-reference-inline").textContent = data.reference;

  if (typeof qrcode !== "undefined") {
    makeQR(document.getElementById("bank-qr-container-inline"), buildEpcQrString(data), 220, "L");
  }

  qrSection.classList.remove("hidden");
  actions.style.display = "";
}

async function confirmBankTransferPayment() {
  const btn = document.getElementById("bank-confirm-btn-inline");
  btn.disabled = true;
  btn.textContent = "\u2026";

  try {
    const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/bar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes: "Überweisung (EPC QR)" }),
    });
    if (res.ok) {
      currentData = await res.json();
      renderInfo();
      renderMaterial();
      closePayModal();
    } else {
      const err = await res.json();
      btn.disabled = false;
      btn.textContent = "\u2713 Bezahlt";
      alert("Fehler: " + (err.detail || "Unbekannter Fehler"));
    }
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "\u2713 Bezahlt";
    alert("Netzwerkfehler");
  }
}

// ── Delete Laufzettel ─────────────────────────────────────────────────────────

function openDeleteModal() {
  document.getElementById("delete-lz-id-display").textContent = LAUFZETTEL_ID;
  document.getElementById("delete-lz-modal").classList.remove("hidden");
}

function closeDeleteModal() {
  document.getElementById("delete-lz-modal").classList.add("hidden");
  document.getElementById("delete-lz-admin-section").classList.add("hidden");
  document.getElementById("delete-lz-admin-pw").value = "";
  document.getElementById("delete-lz-confirm").textContent = "Ja, endgültig löschen";
}

async function confirmDeleteLaufzettel() {
  const confirmBtn = document.getElementById("delete-lz-confirm");
  const adminSection = document.getElementById("delete-lz-admin-section");
  const adminPw = document.getElementById("delete-lz-admin-pw");

  // If the password field is visible, verify admin first then retry
  if (!adminSection.classList.contains("hidden")) {
    const pw = adminPw.value.trim();
    if (!pw) {
      adminPw.focus();
      return;
    }
    confirmBtn.disabled = true;
    confirmBtn.textContent = "Verifiziere…";
    try {
      const formData = new FormData();
      formData.append("password", pw);
      const vRes = await fetch("/api/auth/verify-admin", {
        method: "POST",
        body: formData,
      });
      if (!vRes.ok) {
        const err = await vRes.json().catch(() => ({}));
        alert("Falsches Passwort: " + (err.detail || vRes.status));
        confirmBtn.disabled = false;
        confirmBtn.textContent = "Löschen bestätigen";
        adminPw.focus();
        return;
      }
    } catch (e) {
      alert(`Fehler: ${e.message}`);
      confirmBtn.disabled = false;
      confirmBtn.textContent = "Löschen bestätigen";
      return;
    }
  }

  confirmBtn.disabled = true;
  confirmBtn.textContent = "Wird gelöscht…";
  try {
    const response = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}`, { method: "DELETE" });
    if (response.ok) {
      const dest = _fromParam === "kasse" ? "/kasse" : _fromParam === "member" ? "/member/laufzettel" : "/laufzettel";
      window.location.href = dest;
    } else if (response.status === 403) {
      // Admin verification required — show password field
      adminSection.classList.remove("hidden");
      confirmBtn.disabled = false;
      confirmBtn.textContent = "Löschen bestätigen";
      adminPw.focus();
    } else {
      const err = await response.json().catch(() => ({}));
      alert(`Fehler beim Löschen: ${err.detail || response.status}`);
      confirmBtn.disabled = false;
      confirmBtn.textContent = "Ja, endgültig löschen";
    }
  } catch (e) {
    alert(`Fehler: ${e.message}`);
    confirmBtn.disabled = false;
    confirmBtn.textContent = "Ja, endgültig löschen";
  }
}

document.getElementById("delete-lz-close").addEventListener("click", closeDeleteModal);
document.getElementById("delete-lz-cancel").addEventListener("click", closeDeleteModal);
document.getElementById("delete-lz-overlay").addEventListener("click", closeDeleteModal);
document.getElementById("delete-lz-confirm").addEventListener("click", confirmDeleteLaufzettel);

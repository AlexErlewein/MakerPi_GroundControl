let currentData = null;
let editingMaterialId = null;
let katalog = [];
let currentMatMode = "freitext";
let selectedVariante = null;
let selectedKategorie = null;
let logoDataUrl = null;
let paymentConfig = { sumup_configured: false };

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
            document.querySelector("main").innerHTML = '<p style="color:var(--danger);padding:20px;">Laufzettel not found.</p>';
            return;
        }
        currentData = await res.json();
        renderInfo();
        renderNodes();
        renderMaterial();
    } catch(e) {
        console.error("loadDetail failed:", e);
        document.querySelector("main").innerHTML = '<p style="color:var(--danger);padding:20px;">Fehler beim Laden: ' + e.message + '</p>';
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
    document.getElementById("view-date").textContent = d.date || "-";
    document.getElementById("view-start").textContent = d.start ? new Date(d.start).toLocaleString() : "-";
    document.getElementById("view-owner").textContent = d.owner_name || "-";
    document.getElementById("view-member-id").textContent = d.member_id || "-";
    document.getElementById("view-uid").textContent = d.uid || "-";
    const locked = !!d.payment_method;
    document.getElementById("edit-info-btn").style.display = locked ? "none" : "";
    document.getElementById("add-spende-btn").style.display = locked ? "none" : "";
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

// Groups: 0% tax items go to "Spenden" (rendered last); others group by location.
function getMatGroupKey(m) {
    if (m.tax_rate === 0) return "__spenden__";
    return getLocationForVariante(m.variante_id); // null = Freitext
}
function getMatGroupLabel(m) {
    if (m.tax_rate === 0) return "Spenden";
    return getLocationForVariante(m.variante_id) || "Freitext";
}
function sortMats(mats) {
    return [...mats].sort((a, b) => {
        const sA = a.tax_rate === 0, sB = b.tax_rate === 0;
        if (sA !== sB) return sA ? 1 : -1;
        const locA = getLocationForVariante(a.variante_id) || "￿";
        const locB = getLocationForVariante(b.variante_id) || "￿";
        return locA.localeCompare(locB) || a.name.localeCompare(b.name);
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
    let lastGroupKey = undefined;
    const rows = [];
    for (const m of sorted) {
        const groupKey = getMatGroupKey(m);
        if (groupKey !== lastGroupKey) {
            rows.push(`<tr class="location-separator"><td colspan="7"><span>${esc(getMatGroupLabel(m))}</span></td></tr>`);
            lastGroupKey = groupKey;
        }
        rowIndex++;
        const mengeCell = buildMengeDisplay(m);
        const priceCell = m.calculated_price != null
            ? `<span class="price-col">${m.calculated_price.toFixed(2)} €</span>`
            : '<span style="color:var(--text-secondary)">-</span>';
        const unitPriceLabel = getUnitPriceLabel(m.variante_id)
            || (m.calculated_price != null && m.menge ? `${(m.calculated_price / m.menge).toFixed(4)} €/${m.unit || "Stk"}` : null);
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

function getKatAndVariante(varianteId) {
    if (!varianteId) return null;
    for (const loc of katalog) {
        for (const kat of (loc.kategorien || [])) {
            for (const v of (kat.varianten || [])) {
                if (v.id === varianteId) return { kat, variante: v };
            }
        }
    }
    return null;
}

function getUnitPriceLabel(varianteId) {
    const found = getKatAndVariante(varianteId);
    if (!found) return null;
    const { kat, variante } = found;
    const pm = kat.pricing_model;
    const suffix = pm === "per_gram" ? "/gr"
        : pm === "per_volume_cm3" ? "/cm³"
        : pm === "per_volume_l" ? "/L"
        : pm === "per_minute" ? "/min"
        : `/${kat.unit || "Stück"}`;
    return `${variante.price.toFixed(2)} €${suffix}`;
}

function getLocationForVariante(varianteId) {
    if (!varianteId) return null;
    for (const loc of katalog) {
        for (const kat of (loc.kategorien || [])) {
            for (const v of (kat.varianten || [])) {
                if (v.id === varianteId) return loc.name;
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

function downloadPDF() {
    const d = currentData;
    const mats = [...(d.material || [])];
    const sorted = sortMats(mats);

    let lastGroupKey = undefined;
    let rowIndex = 0;
    let hasPrice = false;
    let materialRows = "";
    // tax_rate → brutto sum (items with null tax_rate treated as 19%)
    const taxGroups = {};

    for (const m of sorted) {
        const groupKey = getMatGroupKey(m);
        if (groupKey !== lastGroupKey) {
            materialRows += `<tr style="background:#e8f0fe;">
                <td colspan="6" style="padding:5px 10px;font-size:10px;font-weight:700;color:#1a56db;text-transform:uppercase;letter-spacing:0.05em;">${esc(getMatGroupLabel(m))}</td>
            </tr>`;
            lastGroupKey = groupKey;
        }
        rowIndex++;
        const rate = m.tax_rate != null ? m.tax_rate : 19;
        const priceText = m.calculated_price != null ? `${m.calculated_price.toFixed(2)} €` : "-";
        if (m.calculated_price != null) {
            hasPrice = true;
            taxGroups[rate] = (taxGroups[rate] || 0) + m.calculated_price;
        }
        materialRows += `<tr style="border-bottom:1px solid #e5e7eb;">
            <td style="padding:6px 10px;">${rowIndex}</td>
            <td style="padding:6px 10px;">${m.name || ""}</td>
            <td style="padding:6px 10px;">${buildMengeText(m)}</td>
            <td style="padding:6px 10px;">${m.unit || "-"}</td>
            <td style="padding:6px 10px;color:#6b7280;font-size:10px;">${rate} %</td>
            <td style="padding:6px 10px;font-family:monospace;">${priceText}</td>
        </tr>`;
    }

    // Build tax summary table
    let taxSummaryRows = "";
    let totalNetto = 0;
    let totalTax = 0;
    let totalBrutto = 0;
    const sortedRates = Object.keys(taxGroups).map(Number).sort((a, b) => b - a);
    for (const rate of sortedRates) {
        const brutto = taxGroups[rate];
        const netto = brutto / (1 + rate / 100);
        const tax = brutto - netto;
        totalNetto += netto;
        totalTax += tax;
        totalBrutto += brutto;
        taxSummaryRows += `<tr style="border-bottom:1px solid #e5e7eb;">
            <td style="padding:5px 10px;">${rate} %</td>
            <td style="padding:5px 10px;font-family:monospace;text-align:right;">${netto.toFixed(2)} €</td>
            <td style="padding:5px 10px;font-family:monospace;text-align:right;">${tax.toFixed(2)} €</td>
            <td style="padding:5px 10px;font-family:monospace;text-align:right;">${brutto.toFixed(2)} €</td>
        </tr>`;
    }
    if (sortedRates.length > 1) {
        taxSummaryRows += `<tr style="border-top:2px solid #9ca3af;font-weight:700;">
            <td style="padding:6px 10px;">Gesamt</td>
            <td style="padding:6px 10px;font-family:monospace;text-align:right;">${totalNetto.toFixed(2)} €</td>
            <td style="padding:6px 10px;font-family:monospace;text-align:right;">${totalTax.toFixed(2)} €</td>
            <td style="padding:6px 10px;font-family:monospace;text-align:right;color:#057a55;">${totalBrutto.toFixed(2)} €</td>
        </tr>`;
    }

    const taxSummarySection = hasPrice ? `
        <h2 style="font-size:13px;margin:18px 0 6px;">Steuerübersicht</h2>
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <thead>
                <tr style="background:#f3f4f6;border-bottom:2px solid #d1d5db;">
                    <th style="padding:5px 10px;text-align:left;font-size:11px;">MwSt.-Satz</th>
                    <th style="padding:5px 10px;text-align:right;font-size:11px;">Netto</th>
                    <th style="padding:5px 10px;text-align:right;font-size:11px;">MwSt.</th>
                    <th style="padding:5px 10px;text-align:right;font-size:11px;">Brutto</th>
                </tr>
            </thead>
            <tbody>${taxSummaryRows}</tbody>
        </table>
        <div style="text-align:right;font-size:15px;font-weight:700;margin-top:6px;color:#057a55;">
            Gesamtbetrag (Brutto): ${totalBrutto.toFixed(2)} €
        </div>` : "";

    const startStr = d.start ? new Date(d.start).toLocaleString("de-DE") : "-";
    const nodes = (d.nodes || []).join(", ") || "-";

    const logoImg = logoDataUrl
        ? `<img src="${logoDataUrl}" style="height:96px;object-fit:contain;display:block;">`
        : "";

    const content = `<div style="font-family:Arial,sans-serif;font-size:12px;color:#111;padding:24px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
            ${logoImg}
            <div style="text-align:right;">
                <div style="font-size:20px;font-weight:700;">Laufzettel #${d.id}</div>
                <div style="font-size:11px;color:#6b7280;">Erstellt am ${new Date().toLocaleString("de-DE")}</div>
            </div>
        </div>
        <hr style="border:none;border-top:1px solid #d1d5db;margin:0 0 14px;">
        <table style="width:100%;border-collapse:collapse;margin-bottom:18px;">
            <tr>
                <td style="padding:3px 0;color:#6b7280;width:130px;">Name</td>
                <td style="padding:3px 0;font-weight:600;">${d.owner_name || "-"}</td>
                <td style="padding:3px 0;color:#6b7280;width:130px;">Member ID</td>
                <td style="padding:3px 0;font-weight:600;">${d.member_id || "-"}</td>
            </tr>
            <tr>
                <td style="padding:3px 0;color:#6b7280;">Datum</td>
                <td style="padding:3px 0;">${d.date || "-"}</td>
                <td style="padding:3px 0;color:#6b7280;">Start</td>
                <td style="padding:3px 0;">${startStr}</td>
            </tr>
            <tr>
                <td style="padding:3px 0;color:#6b7280;">Tag UID</td>
                <td style="padding:3px 0;font-family:monospace;">${d.uid || "-"}</td>
                <td style="padding:3px 0;color:#6b7280;">Nodes</td>
                <td style="padding:3px 0;">${nodes}</td>
            </tr>
        </table>
        <h2 style="font-size:14px;margin:0 0 8px;">Material</h2>
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="background:#f3f4f6;border-bottom:2px solid #d1d5db;">
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">#</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Name</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Menge / Maße</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Einheit</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">MwSt.</th>
                    <th style="padding:6px 10px;text-align:left;font-size:11px;">Preis (€)</th>
                </tr>
            </thead>
            <tbody>${materialRows || `<tr><td colspan="6" style="padding:8px 10px;color:#9ca3af;">Keine Materialeinträge.</td></tr>`}</tbody>
        </table>
        ${taxSummarySection}
    </div>`;

    const el = document.createElement("div");
    el.innerHTML = content;
    html2pdf().set({
        margin: [10, 12, 10, 12],
        filename: `Laufzettel-${d.id}.pdf`,
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
    }).from(el).save();
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
    setMatMode("freitext");
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
            document.getElementById("field-mat-unit-price").value =
                parseFloat((mat.calculated_price / mat.menge).toFixed(6));
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
    sel.innerHTML = '<option value="">-- Standort wählen --</option>' +
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

    if (!locId) { katSel.disabled = true; return; }
    const loc = katalog.find((l) => l.id === locId);
    if (!loc) { katSel.disabled = true; return; }

    katSel.innerHTML = '<option value="">-- Kategorie wählen --</option>' +
        (loc.kategorien || []).map((k) => `<option value="${k.id}">${esc(k.name)}</option>`).join("");
    katSel.disabled = false;
}

function onKatKategorieChange() {
    const locId = parseInt(document.getElementById("kat-select-location").value);
    const katId = parseInt(document.getElementById("kat-select-kategorie").value);
    const varSel = document.getElementById("kat-select-variante");

    varSel.innerHTML = '<option value="">-- Variante wählen --</option>';
    varSel.disabled = true;
    selectedVariante = null;
    selectedKategorie = null;
    hideKatInputFields();
    hidePricePreview();

    if (!katId) return;
    const loc = katalog.find((l) => l.id === locId);
    const kat = (loc && loc.kategorien) ? loc.kategorien.find((k) => k.id === katId) : undefined;
    if (!kat) return;

    selectedKategorie = kat;
    varSel.innerHTML = '<option value="">-- Variante wählen --</option>' +
        (kat.varianten || []).map((v) => `<option value="${v.id}">${esc(v.name)} (${v.price.toFixed(4)} €)</option>`).join("");
    varSel.disabled = false;
    showKatInputFields(kat.pricing_model, kat.unit);
}

function onKatVarianteChange() {
    const varId = parseInt(document.getElementById("kat-select-variante").value);
    hidePricePreview();
    if (!varId || !selectedKategorie) { selectedVariante = null; return; }
    selectedVariante = (selectedKategorie.varianten ? selectedKategorie.varianten.find((v) => v.id === varId) : null) || null;
    recalcPrice();
}

function showKatInputFields(pricingModel, unit) {
    const isVolume = pricingModel === "per_volume_cm3" || pricingModel === "per_volume_l";
    document.getElementById("kat-fields-gram").classList.toggle("hidden", pricingModel !== "per_gram");
    document.getElementById("kat-fields-volume").classList.toggle("hidden", !isVolume);
    document.getElementById("kat-fields-minute").classList.toggle("hidden", pricingModel !== "per_minute");
    document.getElementById("kat-fields-unit").classList.toggle("hidden", pricingModel !== "per_unit");
    const unitLabel = unit ? `(${unit})` : "";
    document.getElementById("kat-gram-label").textContent = unitLabel;
    document.getElementById("kat-unit-label").textContent = unitLabel;
    // attach live recalc listeners
    ["kat-menge-gram", "kat-menge-minute", "kat-menge-unit", "kat-laenge", "kat-breite", "kat-hoehe"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.oninput = recalcPrice;
    });
}

function hideKatInputFields() {
    ["kat-fields-gram", "kat-fields-volume", "kat-fields-minute", "kat-fields-unit"].forEach((id) =>
        document.getElementById(id).classList.add("hidden")
    );
}

function recalcPrice() {
    if (!selectedVariante || !selectedKategorie) { hidePricePreview(); return; }
    const pm = selectedKategorie.pricing_model;
    let price = null;

    if (pm === "per_gram") {
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
        const l = parseFloat(document.getElementById("kat-laenge").value);
        const b = parseFloat(document.getElementById("kat-breite").value);
        const h = parseFloat(document.getElementById("kat-hoehe").value);
        if (!isNaN(l) && !isNaN(b) && !isNaN(h) && l > 0 && b > 0 && h > 0) {
            price = (l * b * h / 1000) * selectedVariante.price;
        }
    } else if (pm === "per_minute") {
        const menge = parseFloat(document.getElementById("kat-menge-minute").value);
        if (!isNaN(menge) && menge > 0) price = menge * selectedVariante.price;
    } else {
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
        const pm = selectedKategorie.pricing_model;
        body.variante_id = selectedVariante.id;
        body.unit = selectedKategorie.unit || null;
        body.name = `${selectedKategorie.name} – ${selectedVariante.name}`;
        body.tax_rate = selectedKategorie.tax_rate != null ? selectedKategorie.tax_rate : 19;

        if (pm === "per_gram") {
            const menge = parseFloat(document.getElementById("kat-menge-gram").value);
            if (isNaN(menge) || menge <= 0) { alert("Bitte gültige Menge eingeben."); return; }
            body.menge = menge;
            body.calculated_price = parseFloat((menge * selectedVariante.price).toFixed(4));
        } else if (pm === "per_volume_cm3") {
            const l = parseFloat(document.getElementById("kat-laenge").value);
            const b = parseFloat(document.getElementById("kat-breite").value);
            const h = parseFloat(document.getElementById("kat-hoehe").value);
            if ([l, b, h].some((v) => isNaN(v) || v <= 0)) { alert("Bitte alle Maße eingeben."); return; }
            body.laenge_cm = l;
            body.breite_cm = b;
            body.hoehe_cm = h;
            body.calculated_price = parseFloat((l * b * h * selectedVariante.price).toFixed(4));
        } else if (pm === "per_volume_l") {
            const l = parseFloat(document.getElementById("kat-laenge").value);
            const b = parseFloat(document.getElementById("kat-breite").value);
            const h = parseFloat(document.getElementById("kat-hoehe").value);
            if ([l, b, h].some((v) => isNaN(v) || v <= 0)) { alert("Bitte alle Maße eingeben."); return; }
            body.laenge_cm = l;
            body.breite_cm = b;
            body.hoehe_cm = h;
            body.calculated_price = parseFloat(((l * b * h / 1000) * selectedVariante.price).toFixed(4));
        } else if (pm === "per_minute") {
            const menge = parseFloat(document.getElementById("kat-menge-minute").value);
            if (isNaN(menge) || menge <= 0) { alert("Bitte gültige Dauer eingeben."); return; }
            body.menge = menge;
            body.unit = "min";
            body.calculated_price = parseFloat((menge * selectedVariante.price).toFixed(4));
        } else {
            const menge = parseFloat(document.getElementById("kat-menge-unit").value);
            if (isNaN(menge) || menge <= 0) { alert("Bitte gültige Menge eingeben."); return; }
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
        document.getElementById("field-mat-total-price").value =
            parseFloat((menge * unitPrice).toFixed(4));
    }
}

function recalcFreitextUnitPrice() {
    const menge = parseFloat(document.getElementById("field-mat-menge").value);
    const total = parseFloat(document.getElementById("field-mat-total-price").value);
    if (!isNaN(menge) && menge > 0 && !isNaN(total) && total >= 0) {
        document.getElementById("field-mat-unit-price").value =
            parseFloat((total / menge).toFixed(6));
    }
}

document.getElementById("field-mat-menge").addEventListener("input", recalcFreitextTotal);
document.getElementById("field-mat-unit-price").addEventListener("input", recalcFreitextTotal);
document.getElementById("field-mat-total-price").addEventListener("input", recalcFreitextUnitPrice);

document.getElementById("add-material-btn").addEventListener("click", openAddMaterial);
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("cancel-mat-btn").addEventListener("click", closeModal);
document.getElementById("modal-overlay").addEventListener("click", closeModal);
document.getElementById("refresh-btn").addEventListener("click", loadDetail);

// ── Spende Modal ──────────────────────────────────────────────

function openSpendeModal() {
    document.getElementById("field-spende-name").value = "Spende";
    document.getElementById("field-spende-amount").value = "";
    document.getElementById("spende-modal").classList.remove("hidden");
    document.getElementById("field-spende-amount").focus();
}
function closeSpendeModal() {
    document.getElementById("spende-modal").classList.add("hidden");
}

document.getElementById("spende-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("field-spende-name").value.trim() || "Spende";
    const amount = parseFloat(document.getElementById("field-spende-amount").value);
    if (isNaN(amount) || amount <= 0) { alert("Bitte gültigen Betrag eingeben."); return; }
    const body = { name, calculated_price: parseFloat(amount.toFixed(2)), tax_rate: 0 };
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

loadKatalog();
loadLogo();
loadPaymentConfig().then(() => loadDetail());

// ── Payment UI ────────────────────────────────────────────────

function getTotal() {
    const mats = (currentData && currentData.material) ? currentData.material : [];
    return mats.reduce((sum, m) => sum + (m.calculated_price != null ? m.calculated_price : 0), 0);
}

function fmtEur(val) {
    return val.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
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
    const karteBtn = document.getElementById("pay-karte-btn");

    if (!paymentConfig.sumup_configured) karteBtn.style.display = "none";

    const checkoutBtn = document.getElementById("pay-checkout-btn");
    if (!paymentConfig.checkout_link_available) checkoutBtn.style.display = "none";

    if (locked) {
        buttons.classList.add("hidden");
        banner.classList.remove("hidden");
        const methodLabels = { bar: "Bar bezahlt", karte: "Per Karte bezahlt" };
        const label = methodLabels[d.payment_method] || "Bezahlt";
        const paidDate = d.paid_at ? new Date(d.paid_at).toLocaleString("de-DE") : "";
        document.getElementById("payment-locked-text").textContent =
            `${label}${paidDate ? " – " + paidDate : ""}`;
        // Lock material table actions
        document.querySelectorAll("#material-body .btn-danger, #material-body .btn-secondary").forEach(
            (btn) => { btn.disabled = true; btn.style.opacity = "0.4"; btn.style.cursor = "not-allowed"; }
        );
    } else {
        buttons.classList.remove("hidden");
        banner.classList.add("hidden");
    }
}

// Bar modal
function openBarModal() {
    const total = getTotal();
    document.getElementById("bar-total-display").textContent = fmtEur(total);
    document.getElementById("bar-modal").classList.remove("hidden");
}
function closeBarModal() {
    document.getElementById("bar-modal").classList.add("hidden");
}
async function confirmBarPayment() {
    const btn = document.getElementById("bar-confirm-btn");
    btn.disabled = true;
    btn.textContent = "…";
    const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/bar`, { method: "POST" });
    btn.disabled = false;
    btn.textContent = "Bezahlt ✓";
    if (res.ok) {
        currentData = await res.json();
        renderInfo();
        renderMaterial();
        closeBarModal();
    } else {
        const err = await res.json();
        alert("Fehler: " + (err.detail || "Unbekannter Fehler"));
    }
}
document.getElementById("bar-modal-close").addEventListener("click", closeBarModal);
document.getElementById("bar-cancel-btn").addEventListener("click", closeBarModal);
document.getElementById("bar-modal-overlay").addEventListener("click", closeBarModal);

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
            signal: kartePollAbort.signal
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
            <button type="button" class="btn btn-success" id="karte-switch-confirm-btn" style="width:100%;">
                ✓ Zahlung bestätigen
            </button>`;

        // Generate QR code
        if (typeof QRCode !== "undefined") {
            new QRCode(document.getElementById("karte-qr-canvas"), {
                text: initData.payment_url,
                width: 200,
                height: 200,
                colorDark: "#000000",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.M,
            });
        }

        document.getElementById("karte-switch-confirm-btn").addEventListener("click", async () => {
            const confirmRes = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/pay/karte/confirm-mock`, { method: "POST" });
            if (confirmRes.ok) {
                currentData = await confirmRes.json();
                renderInfo();
                renderMaterial();
                switchDiv.remove();
                statusText.textContent = "✓ Zahlung als bezahlt markiert.";
                statusText.style.color = "var(--success)";
            }
            actions.style.display = "";
        });

        actions.style.display = "";
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
                    method: "DELETE"
                });
            } catch (_) {}
            return;
        }
        
        let pollData;
        try {
            const r = await fetch(
                `/api/laufzettel/${LAUFZETTEL_ID}/pay/karte/status?client_transaction_id=${encodeURIComponent(txnId)}`,
                { signal: kartePollAbort.signal }
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
                statusText.textContent = pollData.status === "CANCELLED"
                    ? "Zahlung abgebrochen."
                    : "Zahlung fehlgeschlagen.";
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
            method: "DELETE"
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

    if (typeof QRCode !== "undefined") {
        new QRCode(document.getElementById("checkout-qr-canvas"), {
            text: initData.checkout_url,
            width: 200,
            height: 200,
            colorDark: "#000000",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.M,
        });
    }

    actions.style.display = "";

    const POLL_INTERVAL_MS = 5000;
    const poll = async () => {
        if (checkoutPollAbort.signal.aborted) return;
        try {
            const r = await fetch(
                `/api/laufzettel/${LAUFZETTEL_ID}/pay/checkout/status?checkout_id=${encodeURIComponent(checkoutCurrentId)}`,
                { signal: checkoutPollAbort.signal }
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
                statusText.textContent = data.status === "EXPIRED"
                    ? "Zahlungslink abgelaufen."
                    : "Zahlung fehlgeschlagen.";
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

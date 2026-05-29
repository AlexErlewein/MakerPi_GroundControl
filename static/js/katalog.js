let katalog = [];
let editMode = false;

const PRICING_LABELS = {
    per_gram: "pro gr",
    per_kilogram: "pro kg",
    per_volume_cm3: "pro cm³",
    per_volume_l: "pro Liter",
    per_cubic_meter: "pro m³",
    per_cubic_deci_meter: "pro dm³",
    per_volume_m3: "pro m³",
    per_area_m2: "pro m²",
    per_area_dm2: "pro dm²",
    per_minute: "pro Minute",
    per_unit: "pro Stück",
};

async function loadKatalog() {
    try {
        const res = await fetch("/api/katalog");
        if (!res.ok) {
            console.error("API error:", res.status, res.statusText);
            const tree = document.getElementById("katalog-tree");
            if (tree) tree.innerHTML = `<p class="empty" style="color:var(--error)">Fehler beim Laden: ${res.status} ${res.statusText}</p>`;
            return;
        }
        katalog = await res.json();
        console.log("Loaded catalog:", katalog);
        renderTree();
    } catch (error) {
        console.error("Failed to load catalog:", error);
        const tree = document.getElementById("katalog-tree");
        if (tree) tree.innerHTML = `<p class="empty" style="color:var(--error)">Netzwerkfehler: ${error.message}</p>`;
    }
}

function renderTree() {
    const tree = document.getElementById("katalog-tree");
    if (katalog.length === 0) {
        tree.innerHTML = '<p class="empty">Noch keine Standorte. Klicke "+ Standort" um zu beginnen.</p>';
        return;
    }
    tree.innerHTML = katalog.map((loc) => renderLocation(loc)).join("");
    const searchInput = document.getElementById("katalog-search");
    if (searchInput && searchInput.value.trim()) filterKatalog();
}

function filterKatalog() {
    const input = document.getElementById("katalog-search");
    if (!input) return;
    const needle = input.value.trim().toLowerCase();

    if (!needle) {
        renderTree();
        return;
    }

    // Expand all collapsed bodies so filtering can see everything
    document.querySelectorAll(".location-body, .kategorie-body, .unterkategorie-body").forEach(b => {
        b.classList.remove("hidden");
    });

    // Show/hide variant rows
    document.querySelectorAll("#katalog-tree tbody tr").forEach(tr => {
        if (tr.querySelector(".empty")) { tr.style.display = "none"; return; }
        tr.style.display = tr.textContent.toLowerCase().includes(needle) ? "" : "none";
    });

    // Hide unterkategorie blocks with no visible rows
    document.querySelectorAll(".unterkategorie-block").forEach(block => {
        const has = [...block.querySelectorAll("tbody tr")].some(tr => tr.style.display !== "none");
        block.style.display = has ? "" : "none";
    });

    // Hide kategorie blocks with no visible unterkategorie blocks
    document.querySelectorAll(".kategorie-block").forEach(block => {
        const has = [...block.querySelectorAll(".unterkategorie-block")].some(b => b.style.display !== "none");
        block.style.display = has ? "" : "none";
    });

    // Hide location blocks with no visible kategorie blocks
    document.querySelectorAll(".location-block").forEach(block => {
        const has = [...block.querySelectorAll(".kategorie-block")].some(b => b.style.display !== "none");
        block.style.display = has ? "" : "none";
    });
}

function renderLocation(loc) {
    const kats = (loc.kategorien || []).map((k) => renderKategorie(k, loc)).join("");
    const actionsClass = editMode ? '' : 'hidden';
    return `
    <div class="location-block" id="loc-${loc.id}">
        <div class="location-header" onclick="toggleLocation(${loc.id})">
            <div class="location-title">
                <span class="location-chevron open" id="chev-${loc.id}">▶</span>
                📍 ${esc(loc.name)}
                <span style="color:var(--text-secondary);font-size:0.85rem;">(${loc.kategorien.length} Kategorien)</span>
            </div>
            <div class="location-actions ${actionsClass}" onclick="event.stopPropagation()">
                <button class="btn btn-sm btn-secondary" onclick="openEditLocation(${loc.id})">Bearbeiten</button>
                <button class="btn btn-sm btn-success" onclick="openAddKategorie(${loc.id})">+ Kategorie</button>
                <button class="btn btn-sm btn-danger" onclick="deleteLocation(${loc.id})">Löschen</button>
            </div>
        </div>
        <div class="location-body" id="loc-body-${loc.id}">
            ${kats || '<p class="empty" style="padding:10px 0">Keine Kategorien. Klicke "+ Kategorie".</p>'}
        </div>
    </div>`;
}

function renderKategorie(kat, loc) {
    const ukats = (kat.unterkategorien || []).map((u) => renderUnterkategorie(u, kat, loc)).join("");
    const actionsClass = editMode ? '' : 'hidden';
    return `
    <div class="kategorie-block" id="kat-${kat.id}">
        <div class="kategorie-header" onclick="toggleKategorie(${kat.id})">
            <div class="kategorie-title">
                <span class="kategorie-chevron open" id="chev-kat-${kat.id}">▶</span>
                🗂 ${esc(kat.name)}
            </div>
            <div class="kategorie-actions ${actionsClass}" onclick="event.stopPropagation()">
                <button class="btn btn-sm btn-secondary" onclick="openEditKategorie(${kat.id}, ${loc.id})">Bearbeiten</button>
                <button class="btn btn-sm btn-success" onclick="openAddUnterkategorie(${kat.id})">+ Unterkategorie</button>
                <button class="btn btn-sm btn-danger" onclick="deleteKategorie(${kat.id})">Löschen</button>
            </div>
        </div>
        <div class="kategorie-body" id="kat-body-${kat.id}">
            ${ukats || '<p class="empty" style="padding:6px 0 6px 16px">Keine Unterkategorien. Klicke "+ Unterkategorie".</p>'}
        </div>
    </div>`;
}

function renderUnterkategorie(ukat, kat, loc) {
    const pricingLabel = PRICING_LABELS[ukat.pricing_model] || ukat.pricing_model;
    const unit = ukat.unit ? ukat.unit : "";
    const taxRate = ukat.tax_rate != null ? ukat.tax_rate : 19;
    const rows = (ukat.varianten || []).map((v) => renderVariante(v, ukat)).join("");
    const actionsClass = editMode ? '' : 'hidden';
    const colSpan = editMode ? 3 : 2;
    return `
    <div class="unterkategorie-block" id="ukat-${ukat.id}">
        <div class="unterkategorie-header" onclick="toggleUnterkategorie(${ukat.id})">
            <div class="unterkategorie-title">
                <span class="unterkategorie-chevron open" id="chev-ukat-${ukat.id}">▶</span>
                📁 ${esc(ukat.name)}
                <span class="pricing-badge">${esc(pricingLabel)}</span>
                ${unit ? `<span class="unit-label">[${esc(unit)}]</span>` : ""}
                <span class="pricing-badge">${taxRate} % MwSt.</span>
                ${ukat.is_spende ? `<span class="pricing-badge" style="background:var(--accent);color:#fff;">Spende</span>` : ""}
            </div>
            <div class="unterkategorie-actions ${actionsClass}" onclick="event.stopPropagation()">
                <button class="btn btn-sm btn-secondary" onclick="openEditUnterkategorie(${ukat.id}, ${kat.id})">Bearbeiten</button>
                <button class="btn btn-sm btn-success" onclick="openAddVariante(${ukat.id}, '${esc(ukat.pricing_model)}', '${esc(unit)}')">+ Variante</button>
                <button class="btn btn-sm btn-danger" onclick="deleteUnterkategorie(${ukat.id})">Löschen</button>
            </div>
        </div>
        <div class="unterkategorie-body" id="ukat-body-${ukat.id}">
            <table class="varianten-table">
                <thead>
                    <tr>
                        <th>Variante</th>
                        <th class="${editMode ? 'hidden' : ''}">Preis</th>
                        <th class="${editMode ? '' : 'hidden'}">Preis</th>
                        <th class="${editMode ? '' : 'hidden'}">Aktionen</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows || `<tr><td colspan="${colSpan}" class="empty">Keine Varianten.</td></tr>`}
                </tbody>
            </table>
        </div>
    </div>`;
}

function renderVariante(v, ukat) {
    const pricingLabel = PRICING_LABELS[ukat.pricing_model] || ukat.pricing_model;
    const actionsClass = editMode ? '' : 'hidden';
    return `
    <tr id="var-${v.id}">
        <td>${esc(v.name)}</td>
        <td class="price-cell ${editMode ? 'hidden' : ''}">${v.price.toFixed(4)} € <span style="color:var(--text-secondary);font-size:0.8rem;">${esc(pricingLabel)}</span></td>
        <td class="price-cell ${editMode ? '' : 'hidden'}">${v.price.toFixed(4)} € <span style="color:var(--text-secondary);font-size:0.8rem;">${esc(pricingLabel)}</span></td>
        <td class="actions ${actionsClass}">
            <button class="btn btn-sm btn-secondary" onclick="openEditVariante(${v.id}, ${ukat.id}, '${esc(ukat.pricing_model)}', '${esc(ukat.unit || "")}')">Bearbeiten</button>
            <button class="btn btn-sm btn-danger" onclick="deleteVariante(${v.id})">Löschen</button>
        </td>
    </tr>`;
}

function toggleLocation(id) {
    const body = document.getElementById(`loc-body-${id}`);
    const chev = document.getElementById(`chev-${id}`);
    body.classList.toggle("hidden");
    chev.classList.toggle("open");
}

function toggleKategorie(id) {
    const body = document.getElementById(`kat-body-${id}`);
    const chev = document.getElementById(`chev-kat-${id}`);
    body.classList.toggle("hidden");
    chev.classList.toggle("open");
}

function toggleUnterkategorie(id) {
    const body = document.getElementById(`ukat-body-${id}`);
    const chev = document.getElementById(`chev-ukat-${id}`);
    body.classList.toggle("hidden");
    chev.classList.toggle("open");
}

function toggleEditMode() {
    editMode = !editMode;
    const btn = document.getElementById("edit-mode-btn");
    const bulkBtn = document.getElementById("bulk-import-btn");
    const addLocBtn = document.getElementById("add-location-btn");
    
    if (editMode) {
        btn.textContent = "✓ Fertig";
        btn.classList.remove("btn-primary");
        btn.classList.add("btn-success");
        bulkBtn.classList.remove("hidden");
        addLocBtn.classList.remove("hidden");
    } else {
        btn.textContent = "✎ Bearbeiten";
        btn.classList.remove("btn-success");
        btn.classList.add("btn-primary");
        bulkBtn.classList.add("hidden");
        addLocBtn.classList.add("hidden");
    }
    
    renderTree();
}

function esc(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

// ── Location Modal ─────────────────────────────────────────────

function openAddLocation() {
    document.getElementById("location-modal-title").textContent = "Neuer Standort";
    document.getElementById("location-form").reset();
    document.getElementById("edit-location-id").value = "";
    document.getElementById("location-modal").classList.remove("hidden");
    document.getElementById("field-location-name").focus();
}

function openEditLocation(id) {
    const loc = katalog.find((l) => l.id === id);
    if (!loc) return;
    document.getElementById("location-modal-title").textContent = "Standort bearbeiten";
    document.getElementById("edit-location-id").value = id;
    document.getElementById("field-location-name").value = loc.name;
    document.getElementById("location-modal").classList.remove("hidden");
}

function closeLocationModal() {
    document.getElementById("location-modal").classList.add("hidden");
}

document.getElementById("location-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-location-id").value;
    const body = { name: document.getElementById("field-location-name").value.trim() };
    const url = id ? `/api/katalog/locations/${id}` : "/api/katalog/locations";
    const method = id ? "PUT" : "POST";
    const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (res.ok) { closeLocationModal(); await loadKatalog(); }
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen")); }
});

async function deleteLocation(id) {
    if (!confirm("Standort und alle Kategorien/Unterkategorien/Varianten löschen?")) return;
    const res = await fetch(`/api/katalog/locations/${id}`, { method: "DELETE" });
    if (res.ok) await loadKatalog();
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Löschen fehlgeschlagen")); }
}

document.getElementById("add-location-btn").addEventListener("click", openAddLocation);
document.getElementById("edit-mode-btn").addEventListener("click", toggleEditMode);
document.getElementById("location-modal-close").addEventListener("click", closeLocationModal);
document.getElementById("location-cancel").addEventListener("click", closeLocationModal);
document.getElementById("location-overlay").addEventListener("click", closeLocationModal);

// ── Kategorie Modal ────────────────────────────────────────────

function openAddKategorie(locationId) {
    document.getElementById("kategorie-modal-title").textContent = "Neue Kategorie";
    document.getElementById("kategorie-form").reset();
    document.getElementById("edit-kategorie-id").value = "";
    document.getElementById("edit-kategorie-location-id").value = locationId;
    document.getElementById("kategorie-modal").classList.remove("hidden");
    document.getElementById("field-kat-name").focus();
}

function openEditKategorie(katId, locId) {
    const loc = katalog.find((l) => l.id === locId);
    const kat = (loc && loc.kategorien) ? loc.kategorien.find((k) => k.id === katId) : undefined;
    if (!kat) return;
    document.getElementById("kategorie-modal-title").textContent = "Kategorie bearbeiten";
    document.getElementById("edit-kategorie-id").value = katId;
    document.getElementById("edit-kategorie-location-id").value = locId;
    document.getElementById("field-kat-name").value = kat.name;
    document.getElementById("kategorie-modal").classList.remove("hidden");
}

function closeKategorieModal() {
    document.getElementById("kategorie-modal").classList.add("hidden");
}

document.getElementById("kategorie-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-kategorie-id").value;
    const locationId = document.getElementById("edit-kategorie-location-id").value;
    const body = {
        location_id: parseInt(locationId),
        name: document.getElementById("field-kat-name").value.trim(),
    };
    const url = id ? `/api/katalog/kategorien/${id}` : "/api/katalog/kategorien";
    const method = id ? "PUT" : "POST";
    const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (res.ok) { closeKategorieModal(); await loadKatalog(); }
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen")); }
});

async function deleteKategorie(id) {
    if (!confirm("Kategorie und alle Unterkategorien/Varianten löschen?")) return;
    const res = await fetch(`/api/katalog/kategorien/${id}`, { method: "DELETE" });
    if (res.ok) await loadKatalog();
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Löschen fehlgeschlagen")); }
}

document.getElementById("kategorie-modal-close").addEventListener("click", closeKategorieModal);
document.getElementById("kategorie-cancel").addEventListener("click", closeKategorieModal);
document.getElementById("kategorie-overlay").addEventListener("click", closeKategorieModal);

// ── Unterkategorie Modal ───────────────────────────────────────

function openAddUnterkategorie(kategorieId) {
    document.getElementById("unterkategorie-modal-title").textContent = "Neue Unterkategorie";
    document.getElementById("unterkategorie-form").reset();
    document.getElementById("edit-unterkategorie-id").value = "";
    document.getElementById("edit-unterkategorie-kategorie-id").value = kategorieId;
    document.getElementById("field-ukat-tax-rate").value = "19";
    document.getElementById("field-ukat-is-spende").checked = false;
    document.getElementById("unterkategorie-modal").classList.remove("hidden");
    document.getElementById("field-ukat-name").focus();
}

function findUnterkategorie(ukatId) {
    for (const loc of katalog) {
        for (const kat of (loc.kategorien || [])) {
            for (const ukat of (kat.unterkategorien || [])) {
                if (ukat.id === ukatId) return { ukat, kat, loc };
            }
        }
    }
    return null;
}

function openEditUnterkategorie(ukatId, katId) {
    const found = findUnterkategorie(ukatId);
    if (!found) return;
    const { ukat } = found;
    document.getElementById("unterkategorie-modal-title").textContent = "Unterkategorie bearbeiten";
    document.getElementById("edit-unterkategorie-id").value = ukatId;
    document.getElementById("edit-unterkategorie-kategorie-id").value = katId;
    document.getElementById("field-ukat-name").value = ukat.name;
    document.getElementById("field-ukat-pricing").value = ukat.pricing_model;
    document.getElementById("field-ukat-unit").value = ukat.unit || "";
    document.getElementById("field-ukat-tax-rate").value = String(ukat.tax_rate != null ? ukat.tax_rate : 19);
    document.getElementById("field-ukat-is-spende").checked = !!ukat.is_spende;
    document.getElementById("unterkategorie-modal").classList.remove("hidden");
}

function closeUnterkategorieModal() {
    document.getElementById("unterkategorie-modal").classList.add("hidden");
}

document.getElementById("unterkategorie-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-unterkategorie-id").value;
    const kategorieId = document.getElementById("edit-unterkategorie-kategorie-id").value;
    const body = {
        kategorie_id: parseInt(kategorieId),
        name: document.getElementById("field-ukat-name").value.trim(),
        pricing_model: document.getElementById("field-ukat-pricing").value,
        unit: document.getElementById("field-ukat-unit").value.trim() || null,
        tax_rate: parseFloat(document.getElementById("field-ukat-tax-rate").value),
        is_spende: document.getElementById("field-ukat-is-spende").checked,
    };
    const url = id ? `/api/katalog/unterkategorien/${id}` : "/api/katalog/unterkategorien";
    const method = id ? "PUT" : "POST";
    const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (res.ok) { closeUnterkategorieModal(); await loadKatalog(); }
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen")); }
});

async function deleteUnterkategorie(id) {
    if (!confirm("Unterkategorie und alle Varianten löschen?")) return;
    const res = await fetch(`/api/katalog/unterkategorien/${id}`, { method: "DELETE" });
    if (res.ok) await loadKatalog();
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Löschen fehlgeschlagen")); }
}

document.getElementById("unterkategorie-modal-close").addEventListener("click", closeUnterkategorieModal);
document.getElementById("unterkategorie-cancel").addEventListener("click", closeUnterkategorieModal);
document.getElementById("unterkategorie-overlay").addEventListener("click", closeUnterkategorieModal);

// ── Variante Modal ─────────────────────────────────────────────

let currentVariantePricingModel = "per_unit";
let currentVarianteUnit = "";

function openAddVariante(unterkategorieId, pricingModel, unit) {
    currentVariantePricingModel = pricingModel;
    currentVarianteUnit = unit;
    document.getElementById("variante-modal-title").textContent = "Neue Variante";
    document.getElementById("variante-form").reset();
    document.getElementById("edit-variante-id").value = "";
    document.getElementById("edit-variante-unterkategorie-id").value = unterkategorieId;
    document.getElementById("var-price-hint").textContent = getPriceHint(pricingModel, unit);
    document.getElementById("variante-modal").classList.remove("hidden");
    document.getElementById("field-var-name").focus();
}

function openEditVariante(varId, unterkategorieId, pricingModel, unit) {
    currentVariantePricingModel = pricingModel;
    currentVarianteUnit = unit;
    const found = findUnterkategorie(unterkategorieId);
    const ukat = found ? found.ukat : null;
    const v = (ukat && ukat.varianten) ? ukat.varianten.find((v) => v.id === varId) : undefined;
    if (!v) return;
    document.getElementById("variante-modal-title").textContent = "Variante bearbeiten";
    document.getElementById("edit-variante-id").value = varId;
    document.getElementById("edit-variante-unterkategorie-id").value = unterkategorieId;
    document.getElementById("field-var-name").value = v.name;
    document.getElementById("field-var-price").value = v.price;
    document.getElementById("var-price-hint").textContent = getPriceHint(pricingModel, unit);
    document.getElementById("variante-modal").classList.remove("hidden");
}

function getPriceHint(pricingModel, unit) {
    if (pricingModel === "per_gram") return "€ pro Gramm";
    if (pricingModel === "per_kilogram") return "€ pro Kilogramm";
    if (pricingModel === "per_volume_cm3") return "€ pro cm³";
    if (pricingModel === "per_volume_l") return "€ pro Liter";
    if (pricingModel === "per_minute") return "€ pro Minute";
    return unit ? `€ pro ${unit}` : "€ pro Einheit";
}

function closeVarianteModal() {
    document.getElementById("variante-modal").classList.add("hidden");
}

document.getElementById("variante-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-variante-id").value;
    const unterkategorieId = document.getElementById("edit-variante-unterkategorie-id").value;
    const body = {
        unterkategorie_id: parseInt(unterkategorieId),
        name: document.getElementById("field-var-name").value.trim(),
        price: parseFloat(document.getElementById("field-var-price").value),
    };
    const url = id ? `/api/katalog/varianten/${id}` : "/api/katalog/varianten";
    const method = id ? "PUT" : "POST";
    const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (res.ok) { closeVarianteModal(); await loadKatalog(); }
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen")); }
});

async function deleteVariante(id) {
    if (!confirm("Variante löschen?")) return;
    const res = await fetch(`/api/katalog/varianten/${id}`, { method: "DELETE" });
    if (res.ok) await loadKatalog();
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Löschen fehlgeschlagen")); }
}

document.getElementById("variante-modal-close").addEventListener("click", closeVarianteModal);
document.getElementById("variante-cancel").addEventListener("click", closeVarianteModal);
document.getElementById("variante-overlay").addEventListener("click", closeVarianteModal);

loadKatalog();

document.getElementById("katalog-search").addEventListener("input", filterKatalog);

// ── Bulk Import ─────────────────────────────────────────────────────────────

let bulkKatCounter = 0;
let csvParsedData = null;

const PRICING_OPTIONS = [
    { value: "per_unit",       label: "pro Einheit" },
    { value: "per_gram",       label: "pro Gramm" },
    { value: "per_kilogram",   label: "pro Kilogramm" },
    { value: "per_volume_cm3", label: "pro Volumen cm³" },
    { value: "per_volume_l",   label: "pro Liter" },
    { value: "per_minute",     label: "pro Minute" },
];

function openBulkModal() {
    bulkKatCounter = 0;
    csvParsedData = null;

    const sel = document.getElementById("bulk-standort-select");
    sel.innerHTML = katalog.map(
        (loc) => `<option value="${esc(loc.name)}">${esc(loc.name)}</option>`
    ).join("");
    sel.insertAdjacentHTML(
        "beforeend",
        `<option value="__new__">-- Neuen Standort erstellen --</option>`
    );

    document.getElementById("bulk-new-standort-group").style.display = "none";
    document.getElementById("bulk-new-standort-name").value = "";
    document.getElementById("bulk-kat-list").innerHTML = "";
    document.getElementById("csv-preview").classList.add("hidden");
    document.getElementById("bulk-csv-save").classList.add("hidden");
    document.getElementById("bulk-csv-file").value = "";
    switchBulkTab("entry");

    document.getElementById("bulk-modal").classList.remove("hidden");
}

function closeBulkModal() {
    document.getElementById("bulk-modal").classList.add("hidden");
}

function switchBulkTab(tabName) {
    document.querySelectorAll(".bulk-tab-btn").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.tab === tabName);
    });
    document.querySelectorAll(".bulk-tab-panel").forEach((panel) => {
        panel.classList.toggle("hidden", panel.id !== `bulk-tab-${tabName}`);
    });
}

function buildPricingOptions(selectedValue) {
    return PRICING_OPTIONS.map(
        (o) => `<option value="${o.value}"${o.value === selectedValue ? " selected" : ""}>${o.label}</option>`
    ).join("");
}

function addKategorieRow(prefill = {}) {
    const idx      = bulkKatCounter++;
    const name     = prefill.name          || "";

    const html = `
    <div class="bulk-kat-block" data-kat-index="${idx}">
        <div class="bulk-kat-header">
            <span class="bulk-kat-label">Kategorie ${idx + 1}</span>
            <button type="button" class="btn btn-sm btn-danger bulk-remove-kat">−</button>
        </div>
        <div class="bulk-kat-fields">
            <div class="form-group">
                <label>Name</label>
                <input type="text" class="kat-name" placeholder="z.B. Ton" value="${esc(name)}">
            </div>
        </div>
        <div class="bulk-ukat-list" data-kat-index="${idx}"></div>
        <button type="button" class="btn btn-sm btn-secondary bulk-add-ukat" data-kat-index="${idx}">+ Unterkategorie</button>
    </div>`;

    document.getElementById("bulk-kat-list").insertAdjacentHTML("beforeend", html);

    if (prefill.unterkategorien) {
        prefill.unterkategorien.forEach((u) => addUnterkategorieRow(idx, u));
    } else if (prefill.varianten && prefill.varianten.length > 0) {
        // Old-format backward compat: wrap in a "Standard" unterkategorie row
        addUnterkategorieRow(idx, {
            name: "Standard",
            pricing_model: prefill.pricing_model || "per_unit",
            unit: prefill.unit || "",
            tax_rate: prefill.tax_rate != null ? prefill.tax_rate : 19,
            varianten: prefill.varianten,
        });
    }
}

let bulkUkatCounters = {};

function addUnterkategorieRow(katIndex, prefill = {}) {
    if (!bulkUkatCounters[katIndex]) bulkUkatCounters[katIndex] = 0;
    const ukatIdx  = bulkUkatCounters[katIndex]++;
    const name     = prefill.name          || "";
    const pricing  = prefill.pricing_model || "per_unit";
    const unit     = prefill.unit          || "";
    const tax      = prefill.tax_rate      != null ? prefill.tax_rate : 19;

    const html = `
    <div class="bulk-ukat-block" data-kat-index="${katIndex}" data-ukat-index="${ukatIdx}">
        <div class="bulk-kat-header">
            <span class="bulk-kat-label" style="padding-left:16px;">↳ Unterkategorie ${ukatIdx + 1}</span>
            <button type="button" class="btn btn-sm btn-danger bulk-remove-ukat">−</button>
        </div>
        <div class="bulk-kat-fields" style="padding-left:16px;">
            <div class="form-group">
                <label>Name</label>
                <input type="text" class="ukat-name" placeholder="z.B. Standard" value="${esc(name)}">
            </div>
            <div class="form-group">
                <label>Preismodell</label>
                <select class="ukat-pricing">${buildPricingOptions(pricing)}</select>
            </div>
            <div class="form-group">
                <label>Einheit <span class="optional">(Anzeige)</span></label>
                <input type="text" class="ukat-unit" placeholder="z.B. g" value="${esc(unit)}">
            </div>
            <div class="form-group">
                <label>Steuersatz</label>
                <select class="ukat-tax">
                    <option value="19"${tax == 19 ? " selected" : ""}>19 % (Regelsteuersatz)</option>
                    <option value="7"${tax == 7  ? " selected" : ""}>7 % (ermäßigt)</option>
                    <option value="0"${tax == 0  ? " selected" : ""}>0 % (steuerfrei)</option>
                </select>
            </div>
        </div>
        <div class="bulk-var-list" data-kat-index="${katIndex}" data-ukat-index="${ukatIdx}"></div>
        <button type="button" class="btn btn-sm btn-secondary bulk-add-var" data-kat-index="${katIndex}" data-ukat-index="${ukatIdx}" style="margin-left:16px;">+ Variante</button>
    </div>`;

    const ukatList = document.querySelector(`.bulk-ukat-list[data-kat-index="${katIndex}"]`);
    if (ukatList) ukatList.insertAdjacentHTML("beforeend", html);

    if (prefill.varianten) {
        prefill.varianten.forEach((v) => addVarianteRow(katIndex, ukatIdx, v));
    }
}

function addVarianteRow(katIndex, ukatIdx, prefill = {}) {
    const name  = prefill.name  || "";
    const price = prefill.price != null ? prefill.price : "";

    const html = `
    <div class="bulk-var-row" style="padding-left:32px;">
        <input type="text"   class="var-name"  placeholder="Varianten-Name" value="${esc(name)}">
        <input type="number" class="var-price" placeholder="Preis" step="any" min="0" value="${price !== "" ? price : ""}">
        <button type="button" class="btn btn-sm btn-danger bulk-remove-var">−</button>
    </div>`;

    const varList = document.querySelector(`.bulk-var-list[data-kat-index="${katIndex}"][data-ukat-index="${ukatIdx}"]`);
    if (varList) varList.insertAdjacentHTML("beforeend", html);
}

// Event delegation for dynamic elements inside bulk-kat-list
document.getElementById("bulk-kat-list").addEventListener("click", (e) => {
    if (e.target.classList.contains("bulk-remove-kat")) {
        e.target.closest(".bulk-kat-block").remove();
    }
    if (e.target.classList.contains("bulk-remove-ukat")) {
        e.target.closest(".bulk-ukat-block").remove();
    }
    if (e.target.classList.contains("bulk-remove-var")) {
        e.target.closest(".bulk-var-row").remove();
    }
    if (e.target.classList.contains("bulk-add-ukat")) {
        addUnterkategorieRow(parseInt(e.target.dataset.katIndex, 10));
    }
    if (e.target.classList.contains("bulk-add-var")) {
        addVarianteRow(
            parseInt(e.target.dataset.katIndex, 10),
            parseInt(e.target.dataset.ukatIndex, 10)
        );
    }
});

function collectBulkFormData() {
    const sel = document.getElementById("bulk-standort-select");
    let locationName;
    if (sel.value === "__new__") {
        locationName = document.getElementById("bulk-new-standort-name").value.trim();
        if (!locationName) {
            alert("Bitte den Namen des neuen Standorts eingeben.");
            return null;
        }
    } else {
        locationName = sel.value;
    }

    const kategorien = [];
    document.querySelectorAll(".bulk-kat-block").forEach((katBlock) => {
        const name = katBlock.querySelector(".kat-name").value.trim();
        if (!name) return;

        const unterkategorien = [];
        katBlock.querySelectorAll(".bulk-ukat-block").forEach((ukatBlock) => {
            const ukatName = ukatBlock.querySelector(".ukat-name").value.trim();
            if (!ukatName) return;

            const varianten = [];
            ukatBlock.querySelectorAll(".bulk-var-row").forEach((row) => {
                const vName  = row.querySelector(".var-name").value.trim();
                const vPrice = parseFloat(row.querySelector(".var-price").value);
                if (!vName || isNaN(vPrice)) return;
                varianten.push({ name: vName, price: vPrice });
            });

            unterkategorien.push({
                name: ukatName,
                pricing_model: ukatBlock.querySelector(".ukat-pricing").value,
                unit: ukatBlock.querySelector(".ukat-unit").value.trim() || null,
                tax_rate: parseFloat(ukatBlock.querySelector(".ukat-tax").value),
                varianten,
            });
        });

        kategorien.push({ name, unterkategorien });
    });

    if (kategorien.length === 0) {
        alert("Bitte mindestens eine Kategorie mit Namen hinzufügen.");
        return null;
    }

    return { location_name: locationName, kategorien };
}

async function submitBulkImport(payload) {
    const saveBtn = document.getElementById("bulk-entry-save");
    saveBtn.disabled = true;
    saveBtn.textContent = "Speichert…";

    try {
        const res = await fetch("/api/katalog/bulk-import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (res.ok) {
            const data = await res.json();
            closeBulkModal();
            await loadKatalog();
            alert(
                `Erfolgreich importiert!\n` +
                `Standort: ${data.location.name}\n` +
                `Kategorien erstellt: ${data.created_kategorien}\n` +
                `Varianten erstellt: ${data.created_varianten}`
            );
        } else {
            const err = await res.json();
            alert("Fehler: " + (err.detail || "Import fehlgeschlagen"));
        }
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Alles speichern";
    }
}

// CSV pricing model aliases: accept CSV names → internal names
const PRICING_MODEL_ALIASES = {
    per_volume_m3: "per_cubic_meter",
};
function normalizePricingModel(pm) {
    return PRICING_MODEL_ALIASES[pm] || pm;
}

// Auto-detect tab vs comma separator from the first line
function detectSeparator(firstLine) {
    const tabs = (firstLine.match(/\t/g) || []).length;
    const commas = (firstLine.match(/,/g) || []).length;
    return tabs > commas ? "\t" : ",";
}

// Minimal RFC 4180-aware CSV line parser (comma only — tabs use simple split)
function parseCSVLine(line) {
    const result = [];
    let current = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (inQuotes) {
            if (ch === '"' && line[i + 1] === '"') { current += '"'; i++; }
            else if (ch === '"') { inQuotes = false; }
            else { current += ch; }
        } else {
            if (ch === '"') { inQuotes = true; }
            else if (ch === ',') { result.push(current); current = ""; }
            else { current += ch; }
        }
    }
    result.push(current);
    return result;
}

function processCsvText(text) {
    const lines = text.split(/\r?\n/).filter((l) => l.trim() !== "");
    if (lines.length < 2) {
        alert("CSV ist leer oder enthält nur den Header.");
        return;
    }

    const sep = detectSeparator(lines[0]);
    const splitLine = (l) => sep === "\t" ? l.split("\t") : parseCSVLine(l);
    const header = splitLine(lines[0]).map((h) => h.trim().toLowerCase());

    const requiredCols = ["standort", "kategorie", "preismodell", "einheit", "steuersatz", "variante", "preis"];
    const missing = requiredCols.filter((c) => !header.includes(c));
    if (missing.length > 0) {
        alert("CSV-Header fehlt Spalten: " + missing.join(", "));
        return;
    }
    const hasUnterkategorie = header.includes("unterkategorie");
    const hasSpende = header.includes("spende");

    const col = (row, name) => {
        const idx = header.indexOf(name);
        return idx >= 0 ? (row[idx] || "").trim() : "";
    };

    const errors = [];
    // Tree: standort → kategorie → ukatKey → ukatData
    const tree = new Map();

    lines.slice(1).forEach((line, i) => {
        const row = splitLine(line);
        const standort       = col(row, "standort");
        const kategorie      = col(row, "kategorie");
        const unterkategorie = hasUnterkategorie ? (col(row, "unterkategorie") || "Standard") : "Standard";
        const preismodell    = normalizePricingModel(col(row, "preismodell") || "per_unit");
        const einheit        = col(row, "einheit") || null;
        const steuersatzStr  = col(row, "steuersatz");
        const spendeStr      = hasSpende ? col(row, "spende") : "";
        const variante       = col(row, "variante");
        const preisStr       = col(row, "preis");

        // Skip stray header-like rows
        if (!kategorie && !variante && standort.includes(",")) return;
        if (preisStr.toLowerCase() === "preis" || preisStr.toLowerCase() === "price") return;

        if (!standort || !kategorie || !variante) {
            errors.push(`Zeile ${i + 2}: standort, kategorie und variante sind Pflicht.`);
            return;
        }

        const steuersatz = steuersatzStr !== "" ? parseFloat(steuersatzStr) : 19;
        const isSpende = spendeStr === "1" || spendeStr.toLowerCase() === "true" || spendeStr.toLowerCase() === "ja";
        const preis = parseFloat(preisStr.replace(",", "."));
        if (isNaN(preis)) {
            errors.push(`Zeile ${i + 2}: Ungültiger Preis "${preisStr}".`);
            return;
        }

        if (!tree.has(standort)) tree.set(standort, new Map());
        const katMap = tree.get(standort);
        if (!katMap.has(kategorie)) katMap.set(kategorie, new Map());
        const ukatMap = katMap.get(kategorie);

        const ukatKey = `${unterkategorie}|${preismodell}|${einheit}|${steuersatz}|${isSpende}`;
        if (!ukatMap.has(ukatKey)) {
            ukatMap.set(ukatKey, { name: unterkategorie, preismodell, einheit, steuersatz, isSpende, varianten: [] });
        }
        ukatMap.get(ukatKey).varianten.push({ name: variante, price: preis });
    });

    if (errors.length > 0) {
        alert("CSV-Fehler:\n" + errors.join("\n"));
        return;
    }

    csvParsedData = [];
    for (const [standort, katMap] of tree.entries()) {
        const kategorien = [];
        for (const [katName, ukatMap] of katMap.entries()) {
            const unterkategorien = [];
            for (const ukatData of ukatMap.values()) {
                unterkategorien.push({
                    name: ukatData.name,
                    pricing_model: ukatData.preismodell,
                    unit: ukatData.einheit,
                    tax_rate: ukatData.steuersatz,
                    is_spende: ukatData.isSpende || false,
                    varianten: ukatData.varianten,
                });
            }
            kategorien.push({ name: katName, unterkategorien });
        }
        csvParsedData.push({ location_name: standort, kategorien });
    }

    renderCsvPreview(csvParsedData);
    document.getElementById("bulk-csv-save").classList.remove("hidden");
}

function parseCsvAndPreview(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const text = e.target.result.replace(/^﻿/, ""); // strip UTF-8 BOM
        if (text.includes("�")) {
            // UTF-8 produced replacement chars — retry as Windows-1252
            const r2 = new FileReader();
            r2.onload = (e2) => processCsvText(e2.target.result.replace(/^﻿/, ""));
            r2.readAsText(file, "windows-1252");
            return;
        }
        processCsvText(text);
    };
    reader.readAsText(file, "utf-8");
}

function renderCsvPreview(payloads) {
    const preview = document.getElementById("csv-preview");
    let html = "";
    for (const payload of payloads) {
        html += `<h4 class="csv-preview-loc">📍 ${esc(payload.location_name)}</h4>`;
        html += `<table class="csv-preview-table">
            <thead>
                <tr>
                    <th>Kategorie</th><th>Unterkategorie</th><th>Preismodell</th>
                    <th>Einheit</th><th>MwSt.</th><th>Variante</th><th>Preis</th>
                </tr>
            </thead><tbody>`;
        for (const kat of payload.kategorien) {
            for (const ukat of (kat.unterkategorien || [])) {
                if (ukat.varianten.length === 0) {
                    html += `<tr>
                        <td>${esc(kat.name)}</td><td>${esc(ukat.name)}</td>
                        <td>${esc(ukat.pricing_model)}</td><td>${esc(ukat.unit || "—")}</td>
                        <td>${ukat.tax_rate} %</td>
                        <td colspan="2" style="color:var(--text-secondary)">Keine Varianten</td>
                    </tr>`;
                } else {
                    ukat.varianten.forEach((v, vi) => {
                        if (vi === 0) {
                            html += `<tr>
                                <td rowspan="${ukat.varianten.length}">${esc(kat.name)}</td>
                                <td rowspan="${ukat.varianten.length}">${esc(ukat.name)}</td>
                                <td rowspan="${ukat.varianten.length}">${esc(ukat.pricing_model)}</td>
                                <td rowspan="${ukat.varianten.length}">${esc(ukat.unit || "—")}</td>
                                <td rowspan="${ukat.varianten.length}">${ukat.tax_rate} %</td>
                                <td>${esc(v.name)}</td><td>${v.price.toFixed(4)} €</td>
                            </tr>`;
                        } else {
                            html += `<tr><td>${esc(v.name)}</td><td>${v.price.toFixed(4)} €</td></tr>`;
                        }
                    });
                }
            }
        }
        html += `</tbody></table>`;
    }
    preview.innerHTML = html;
    preview.classList.remove("hidden");
}

async function importFromCsvPreview() {
    if (!csvParsedData || csvParsedData.length === 0) return;

    const saveBtn = document.getElementById("bulk-csv-save");
    saveBtn.disabled = true;
    saveBtn.textContent = "Importiert…";

    let totalKat = 0, totalVar = 0;
    const errors = [];

    for (const payload of csvParsedData) {
        try {
            const res = await fetch("/api/katalog/bulk-import", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (res.ok) {
                const data = await res.json();
                totalKat += data.created_kategorien;
                totalVar += data.created_varianten;
            } else {
                const err = await res.json();
                errors.push(`${payload.location_name}: ${err.detail || "Fehler"}`);
            }
        } catch (_) {
            errors.push(`${payload.location_name}: Netzwerkfehler`);
        }
    }

    saveBtn.disabled = false;
    saveBtn.textContent = "CSV importieren";

    if (errors.length > 0) {
        alert("Einige Standorte konnten nicht importiert werden:\n" + errors.join("\n"));
    }
    if (totalKat > 0 || totalVar > 0) {
        closeBulkModal();
        await loadKatalog();
        alert(
            `CSV-Import abgeschlossen!\nKategorien erstellt: ${totalKat}\nVarianten erstellt: ${totalVar}`
        );
    }
}

// Event wiring
document.getElementById("bulk-import-btn").addEventListener("click", openBulkModal);
document.getElementById("bulk-modal-close").addEventListener("click", closeBulkModal);
document.getElementById("bulk-overlay").addEventListener("click", closeBulkModal);
document.getElementById("bulk-entry-cancel").addEventListener("click", closeBulkModal);
document.getElementById("bulk-csv-cancel").addEventListener("click", closeBulkModal);

document.querySelectorAll(".bulk-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchBulkTab(btn.dataset.tab));
});

document.getElementById("bulk-add-kat-btn").addEventListener("click", () => addKategorieRow());

document.getElementById("bulk-standort-select").addEventListener("change", (e) => {
    const newGroup = document.getElementById("bulk-new-standort-group");
    newGroup.style.display = e.target.value === "__new__" ? "block" : "none";
    if (e.target.value === "__new__") {
        document.getElementById("bulk-new-standort-name").focus();
    }
});

document.getElementById("bulk-entry-save").addEventListener("click", async () => {
    const payload = collectBulkFormData();
    if (!payload) return;
    await submitBulkImport(payload);
});

document.getElementById("bulk-csv-file").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    parseCsvAndPreview(file);
});

document.getElementById("bulk-csv-save").addEventListener("click", importFromCsvPreview);

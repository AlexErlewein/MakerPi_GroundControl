let katalog = [];

const PRICING_LABELS = {
    per_gram: "pro g",
    per_volume_cm3: "pro cm³",
    per_volume_l: "pro Liter",
    per_unit: "pro Stück",
};

async function loadKatalog() {
    const res = await fetch("/api/katalog");
    katalog = await res.json();
    renderTree();
}

function renderTree() {
    const tree = document.getElementById("katalog-tree");
    if (katalog.length === 0) {
        tree.innerHTML = '<p class="empty">Noch keine Standorte. Klicke "+ Standort" um zu beginnen.</p>';
        return;
    }
    tree.innerHTML = katalog.map((loc) => renderLocation(loc)).join("");
}

function renderLocation(loc) {
    const kats = (loc.kategorien || []).map((k) => renderKategorie(k, loc)).join("");
    return `
    <div class="location-block" id="loc-${loc.id}">
        <div class="location-header" onclick="toggleLocation(${loc.id})">
            <div class="location-title">
                <span class="location-chevron open" id="chev-${loc.id}">▶</span>
                📍 ${esc(loc.name)}
                <span style="color:var(--text-secondary);font-size:0.85rem;">(${loc.kategorien.length} Kategorien)</span>
            </div>
            <div class="location-actions" onclick="event.stopPropagation()">
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
    const pricingLabel = PRICING_LABELS[kat.pricing_model] || kat.pricing_model;
    const unit = kat.unit ? kat.unit : "";
    const rows = (kat.varianten || []).map((v) => renderVariante(v, kat)).join("");
    return `
    <div class="kategorie-block" id="kat-${kat.id}">
        <div class="kategorie-header">
            <div class="kategorie-title">
                🗂 ${esc(kat.name)}
                <span class="pricing-badge">${esc(pricingLabel)}</span>
                ${unit ? `<span class="unit-label">[${esc(unit)}]</span>` : ""}
            </div>
            <div class="kategorie-actions">
                <button class="btn btn-sm btn-secondary" onclick="openEditKategorie(${kat.id}, ${loc.id})">Bearbeiten</button>
                <button class="btn btn-sm btn-success" onclick="openAddVariante(${kat.id}, '${esc(kat.pricing_model)}', '${esc(unit)}')">+ Variante</button>
                <button class="btn btn-sm btn-danger" onclick="deleteKategorie(${kat.id})">Löschen</button>
            </div>
        </div>
        <table class="varianten-table">
            <thead>
                <tr><th>Variante</th><th>Preis</th><th>Aktionen</th></tr>
            </thead>
            <tbody>
                ${rows || `<tr><td colspan="3" class="empty">Keine Varianten.</td></tr>`}
            </tbody>
        </table>
    </div>`;
}

function renderVariante(v, kat) {
    const pricingLabel = PRICING_LABELS[kat.pricing_model] || kat.pricing_model;
    return `
    <tr id="var-${v.id}">
        <td>${esc(v.name)}</td>
        <td class="price-cell">${v.price.toFixed(4)} € <span style="color:var(--text-secondary);font-size:0.8rem;">${esc(pricingLabel)}</span></td>
        <td class="actions">
            <button class="btn btn-sm btn-secondary" onclick="openEditVariante(${v.id}, ${kat.id}, '${esc(kat.pricing_model)}', '${esc(kat.unit || "")}')">Bearbeiten</button>
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
    if (!confirm("Standort und alle Kategorien/Varianten löschen?")) return;
    const res = await fetch(`/api/katalog/locations/${id}`, { method: "DELETE" });
    if (res.ok) await loadKatalog();
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Löschen fehlgeschlagen")); }
}

document.getElementById("add-location-btn").addEventListener("click", openAddLocation);
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
    const kat = loc?.kategorien?.find((k) => k.id === katId);
    if (!kat) return;
    document.getElementById("kategorie-modal-title").textContent = "Kategorie bearbeiten";
    document.getElementById("edit-kategorie-id").value = katId;
    document.getElementById("edit-kategorie-location-id").value = locId;
    document.getElementById("field-kat-name").value = kat.name;
    document.getElementById("field-kat-pricing").value = kat.pricing_model;
    document.getElementById("field-kat-unit").value = kat.unit || "";
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
        pricing_model: document.getElementById("field-kat-pricing").value,
        unit: document.getElementById("field-kat-unit").value.trim() || null,
    };
    const url = id ? `/api/katalog/kategorien/${id}` : "/api/katalog/kategorien";
    const method = id ? "PUT" : "POST";
    const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (res.ok) { closeKategorieModal(); await loadKatalog(); }
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen")); }
});

async function deleteKategorie(id) {
    if (!confirm("Kategorie und alle Varianten löschen?")) return;
    const res = await fetch(`/api/katalog/kategorien/${id}`, { method: "DELETE" });
    if (res.ok) await loadKatalog();
    else { const err = await res.json(); alert("Fehler: " + (err.detail || "Löschen fehlgeschlagen")); }
}

document.getElementById("kategorie-modal-close").addEventListener("click", closeKategorieModal);
document.getElementById("kategorie-cancel").addEventListener("click", closeKategorieModal);
document.getElementById("kategorie-overlay").addEventListener("click", closeKategorieModal);

// ── Variante Modal ─────────────────────────────────────────────

let currentVariantePricingModel = "per_unit";
let currentVarianteUnit = "";

function openAddVariante(kategorieId, pricingModel, unit) {
    currentVariantePricingModel = pricingModel;
    currentVarianteUnit = unit;
    document.getElementById("variante-modal-title").textContent = "Neue Variante";
    document.getElementById("variante-form").reset();
    document.getElementById("edit-variante-id").value = "";
    document.getElementById("edit-variante-kategorie-id").value = kategorieId;
    document.getElementById("var-price-hint").textContent = getPriceHint(pricingModel, unit);
    document.getElementById("variante-modal").classList.remove("hidden");
    document.getElementById("field-var-name").focus();
}

function openEditVariante(varId, kategorieId, pricingModel, unit) {
    currentVariantePricingModel = pricingModel;
    currentVarianteUnit = unit;
    const loc = katalog.find((l) => l.kategorien?.some((k) => k.id === kategorieId));
    const kat = loc?.kategorien?.find((k) => k.id === kategorieId);
    const v = kat?.varianten?.find((v) => v.id === varId);
    if (!v) return;
    document.getElementById("variante-modal-title").textContent = "Variante bearbeiten";
    document.getElementById("edit-variante-id").value = varId;
    document.getElementById("edit-variante-kategorie-id").value = kategorieId;
    document.getElementById("field-var-name").value = v.name;
    document.getElementById("field-var-price").value = v.price;
    document.getElementById("var-price-hint").textContent = getPriceHint(pricingModel, unit);
    document.getElementById("variante-modal").classList.remove("hidden");
}

function getPriceHint(pricingModel, unit) {
    if (pricingModel === "per_gram") return "€ pro Gramm";
    if (pricingModel === "per_volume_cm3") return "€ pro cm³";
    if (pricingModel === "per_volume_l") return "€ pro Liter";
    return unit ? `€ pro ${unit}` : "€ pro Einheit";
}

function closeVarianteModal() {
    document.getElementById("variante-modal").classList.add("hidden");
}

document.getElementById("variante-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-variante-id").value;
    const kategorieId = document.getElementById("edit-variante-kategorie-id").value;
    const body = {
        kategorie_id: parseInt(kategorieId),
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

document.getElementById("refresh-btn").addEventListener("click", loadKatalog);

loadKatalog();

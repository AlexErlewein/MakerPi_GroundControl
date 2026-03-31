let currentData = null;
let editingMaterialId = null;
let katalog = [];
let currentMatMode = "freitext";
let selectedVariante = null;
let selectedKategorie = null;

// ── Data loading ─────────────────────────────────────────────

async function loadDetail() {
    const res = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}`);
    if (!res.ok) {
        document.querySelector("main").innerHTML = '<p style="color:var(--danger);padding:20px;">Laufzettel not found.</p>';
        return;
    }
    currentData = await res.json();
    renderInfo();
    renderNodes();
    renderMaterial();
}

async function loadKatalog() {
    const res = await fetch("/api/katalog");
    katalog = await res.json();
    populateLocationSelect();
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

function renderMaterial() {
    const tbody = document.getElementById("material-body");
    const mats = currentData.material || [];
    if (mats.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">No material entries yet.</td></tr>';
        return;
    }
    tbody.innerHTML = mats
        .map((m, i) => {
            const mengeCell = buildMengeDisplay(m);
            const priceCell = m.calculated_price != null
                ? `<span class="price-col">${m.calculated_price.toFixed(2)} €</span>`
                : '<span style="color:var(--text-secondary)">-</span>';
            return `
        <tr>
            <td>${i + 1}</td>
            <td>${esc(m.name)}</td>
            <td>${mengeCell}</td>
            <td>${esc(m.unit || "-")}</td>
            <td>${priceCell}</td>
            <td class="actions">
                <button class="btn btn-sm btn-secondary" onclick="openEditMaterial(${m.id})">Bearbeiten</button>
                <button class="btn btn-sm btn-danger" onclick="deleteMaterial(${m.id})">Löschen</button>
            </td>
        </tr>`;
        })
        .join("");
}

function buildMengeDisplay(m) {
    if (m.laenge_cm != null && m.breite_cm != null && m.hoehe_cm != null) {
        const vol = m.laenge_cm * m.breite_cm * m.hoehe_cm;
        return `${m.laenge_cm}×${m.breite_cm}×${m.hoehe_cm} cm <span style="color:var(--text-secondary);font-size:0.8rem;">(${vol.toFixed(1)} cm³)</span>`;
    }
    return m.menge != null ? String(m.menge) : "-";
}

function esc(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
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
    const kat = loc?.kategorien?.find((k) => k.id === katId);
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
    selectedVariante = selectedKategorie.varianten?.find((v) => v.id === varId) || null;
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
        body = {
            name: document.getElementById("field-mat-name").value.trim(),
            menge: parseFloat(document.getElementById("field-mat-menge").value) || null,
            unit: document.getElementById("field-mat-unit").value.trim() || null,
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

document.getElementById("add-material-btn").addEventListener("click", openAddMaterial);
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("cancel-mat-btn").addEventListener("click", closeModal);
document.getElementById("modal-overlay").addEventListener("click", closeModal);
document.getElementById("refresh-btn").addEventListener("click", loadDetail);

loadKatalog();
loadDetail();

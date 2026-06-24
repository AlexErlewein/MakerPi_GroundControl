// Guest Laufzettel Detail JavaScript
// Simplified version of laufzettel-detail.js without payment functionality

let laufzettelData = null;
let allMaterials = [];
let katalog = [];
let editingMaterialId = null;
let currentMatMode = "katalog";  // Guests only use katalog mode
let selectedVariante = null;
let selectedKategorie = null;

// Load Laufzettel data
async function loadLaufzettel() {
    try {
        const response = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}`);
        if (response.ok) {
            laufzettelData = await response.json();
            allMaterials = laufzettelData.material || [];
            renderInfo();
            renderMaterials();
        } else {
            console.error('Failed to load Laufzettel');
        }
    } catch (e) {
        console.error('Error loading Laufzettel:', e);
    }
}

// Render info section
function renderInfo() {
    if (!laufzettelData) return;

    document.getElementById('lz-id-display').textContent = `#${laufzettelData.id}`;
    document.getElementById('view-lz-nr').textContent = laufzettelData.id;
    document.getElementById('view-date').textContent = laufzettelData.date || '-';
    document.getElementById('view-start').textContent = formatTime(laufzettelData.start);
    document.getElementById('view-owner').textContent = laufzettelData.owner_name || '-';
    document.getElementById('view-email').textContent = laufzettelData.guest_email || '-';
    
    // Display NFC status
    const nfcNotLinked = document.getElementById('nfc-not-linked');
    const nfcLinked = document.getElementById('nfc-linked');
    const nfcUidDisplay = document.getElementById('nfc-uid-display');
    
    if (laufzettelData.guest_nfc_uid) {
        nfcNotLinked.classList.add('hidden');
        nfcLinked.classList.remove('hidden');
        nfcUidDisplay.textContent = laufzettelData.guest_nfc_uid;
    } else {
        nfcNotLinked.classList.remove('hidden');
        nfcLinked.classList.add('hidden');
    }
}

// Render materials table
function renderMaterials() {
    const tbody = document.getElementById('material-body');
    const tfoot = document.getElementById('material-total');

    if (allMaterials.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty">Noch keine Materialien erfasst.</td></tr>';
        tfoot.classList.add('hidden');
        return;
    }

    // Group by location, then category (same as member view)
    const sorted = [...allMaterials].sort((a, b) => {
        const locA = getLocationForVariante(a.variante_id) || '￿';
        const locB = getLocationForVariante(b.variante_id) || '￿';
        const catA = getKategorieForVariante(a.variante_id) || '';
        const catB = getKategorieForVariante(b.variante_id) || '';
        return locA.localeCompare(locB) || catA.localeCompare(catB) || a.name.localeCompare(b.name);
    });

    let lastLoc = undefined;
    let lastCat = undefined;
    const rows = [];
    let rowIndex = 0;

    for (const mat of sorted) {
        const loc = getLocationForVariante(mat.variante_id) || 'Freitext';
        const cat = getKategorieForVariante(mat.variante_id);

        if (loc !== lastLoc) {
            rows.push(`<tr class="location-separator"><td colspan="7"><span>${esc(loc)}</span></td></tr>`);
            lastLoc = loc;
            lastCat = undefined;
        }
        if (cat && cat !== lastCat) {
            rows.push(`<tr class="category-separator"><td colspan="7"><span>${esc(cat)}</span></td></tr>`);
            lastCat = cat;
        }

        rowIndex++;
        const mengeStr = buildMengeDisplay(mat);
        const priceStr = mat.calculated_price ? `${mat.calculated_price.toFixed(2)} €` : '-';
        const unitPriceLabel = getUnitPriceLabel(mat.variante_id);
        rows.push(`
            <tr>
                <td>${rowIndex}</td>
                <td>${esc(mat.name)}</td>
                <td>${mengeStr}</td>
                <td>${esc(mat.unit || '-')}</td>
                <td style="color:var(--text-secondary);font-size:0.85rem;white-space:nowrap;">${unitPriceLabel || '-'}</td>
                <td>${priceStr}</td>
                <td class="actions">
                    <button class="btn btn-sm btn-secondary" onclick="editMaterial(${mat.id})">Bearbeiten</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteMaterial(${mat.id})">Löschen</button>
                </td>
            </tr>
        `);
    }

    tbody.innerHTML = rows.join('');

    // Calculate and show total
    const total = allMaterials.reduce((sum, m) => sum + (m.calculated_price || 0), 0);
    if (total > 0) {
        document.getElementById('material-total-value').textContent = `${total.toFixed(2)} €`;
        tfoot.classList.remove('hidden');
    } else {
        tfoot.classList.add('hidden');
    }
}

// Format material quantity/measurements
function buildMengeDisplay(mat) {
    if (mat.laenge_cm != null && mat.breite_cm != null && mat.hoehe_cm != null) {
        const vol = mat.laenge_cm * mat.breite_cm * mat.hoehe_cm;
        return `${mat.laenge_cm}×${mat.breite_cm}×${mat.hoehe_cm} cm <span style="color:var(--text-secondary);font-size:0.8rem;">(${vol.toFixed(1)} cm³)</span>`;
    }
    return mat.menge != null ? String(mat.menge) : "-";
}

function getUkatAndVariante(varianteId) {
    if (!varianteId) return null;
    for (const loc of katalog) {
        for (const kat of (loc.kategorien || [])) {
            for (const ukat of (kat.unterkategorien || [])) {
                for (const v of (ukat.varianten || [])) {
                    if (v.id === varianteId) return { ukat, variante: v, loc };
                }
            }
        }
    }
    return null;
}

function getLocationForVariante(varianteId) {
    if (!varianteId) return null;
    for (const loc of katalog) {
        for (const kat of (loc.kategorien || [])) {
            for (const ukat of (kat.unterkategorien || [])) {
                for (const v of (ukat.varianten || [])) {
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
        for (const kat of (loc.kategorien || [])) {
            for (const ukat of (kat.unterkategorien || [])) {
                for (const v of (ukat.varianten || [])) {
                    if (v.id === varianteId) return kat.name;
                }
            }
        }
    }
    return null;
}

function getUnitPriceLabel(varianteId) {
    const found = getUkatAndVariante(varianteId);
    if (!found) return null;
    const { ukat, variante } = found;
    const pm = variante.pricing_model || ukat.pricing_model;
    const suffix = pm === "per_gram" ? "/gr"
        : pm === "per_kilogram" ? "/kg"
        : pm === "per_volume_cm3" ? "/cm³"
        : pm === "per_volume_l" ? "/L"
        : pm === "per_cubic_meter" ? "/m³"
        : pm === "per_cubic_deci_meter" ? "/dm³"
        : pm === "per_volume_m3" ? "/m³"
        : pm === "per_area_m2" ? "/m²"
        : pm === "per_area_dm2" ? "/dm²"
        : pm === "per_minute" ? "/min"
        : `/${variante.unit || ukat.unit || "Stück"}`;
    return `${variante.price.toFixed(2)} €${suffix}`;
}

// Format time
function formatTime(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
}

// Escape HTML
function esc(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

// Sign out: clear the guest session and return to the login page.
// Without clearing the session, navigating away just bounces back here
// because the guest-form page auto-resumes the active session.
async function guestLogout() {
    try {
        await fetch('/api/guest/logout', { method: 'POST', credentials: 'include' });
    } catch (e) {
        // Ignore network errors; still navigate away
    }
    window.location.href = '/';
}

// Open material modal
function openMaterialModal() {
    editingMaterialId = null;
    document.getElementById('material-form').reset();
    document.getElementById('edit-material-id').value = '';
    document.getElementById('edit-mat-variante-id').value = '';
    document.getElementById('modal-title').textContent = 'Material hinzufügen';
    setMatMode('katalog'); // Guests can only use katalog mode
    document.getElementById('material-modal').classList.remove('hidden');
}

// Edit material
function editMaterial(matId) {
    const mat = allMaterials.find(m => m.id === matId);
    if (!mat) return;

    editingMaterialId = matId;
    document.getElementById('edit-material-id').value = mat.id;
    document.getElementById('edit-mat-variante-id').value = mat.variante_id || '';
    document.getElementById('modal-title').textContent = 'Material bearbeiten';

    if (mat.variante_id) {
        // Load from catalog
        setMatMode('katalog');
        // TODO: Load catalog data and select appropriate options
    } else {
        // Freitext mode (not used for guests, but kept for consistency)
        setMatMode('freitext');
        document.getElementById('field-mat-name').value = mat.name;
        document.getElementById('field-mat-menge').value = mat.menge || '';
        document.getElementById('field-mat-unit').value = mat.unit || '';
        document.getElementById('field-mat-unit-price').value = '';
        document.getElementById('field-mat-total-price').value = mat.calculated_price || '';
        document.getElementById('field-mat-tax-rate').value = mat.tax_rate !== null ? mat.tax_rate : 19;
    }

    document.getElementById('material-modal').classList.remove('hidden');
}

// Close material modal
function closeMaterialModal() {
    document.getElementById('material-modal').classList.add('hidden');
}

// Submit material form (reused from laufzettel-detail.js)
document.getElementById("material-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    // Katalog mode only for guests
    if (!selectedVariante || !selectedKategorie) {
        alert("Bitte Standort, Kategorie und Variante auswählen.");
        return;
    }

    const pm = selectedVariante.pricing_model || 'per_unit';
    let body = {};

    body.variante_id = selectedVariante.id;
    body.unit = selectedVariante.unit || null;
    body.name = `${selectedKategorie.name} – ${selectedVariante.name}`;
    body.tax_rate = selectedKategorie.tax_rate != null ? selectedKategorie.tax_rate : 19;

    if (pm === "per_gram") {
        const menge = parseFloat(document.getElementById("kat-menge-gram").value);
        if (isNaN(menge) || menge <= 0) { alert("Bitte gültige Menge eingeben."); return; }
        body.menge = menge;
        body.calculated_price = parseFloat((menge * selectedVariante.price).toFixed(4));
    } else if (pm === "per_kilogram") {
        const menge = parseFloat(document.getElementById("kat-menge-gram").value);
        if (isNaN(menge) || menge <= 0) { alert("Bitte gültige Menge eingeben."); return; }
        body.menge = menge;
        body.unit = selectedKategorie.unit || "kg";
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
        const liters = parseFloat(document.getElementById("kat-menge-gram").value);
        if (isNaN(liters) || liters <= 0) { alert("Bitte gültige Menge in Litern eingeben."); return; }
        body.menge = liters;
        body.unit = selectedKategorie.unit || "L";
        body.calculated_price = parseFloat((liters * selectedVariante.price).toFixed(4));
    } else if (pm === "per_cubic_meter") {
        const l = parseFloat(document.getElementById("kat-laenge").value);
        const b = parseFloat(document.getElementById("kat-breite").value);
        const h = parseFloat(document.getElementById("kat-hoehe").value);
        if ([l, b, h].some((v) => isNaN(v) || v <= 0)) { alert("Bitte alle Maße eingeben."); return; }
        body.laenge_cm = l;
        body.breite_cm = b;
        body.hoehe_cm = h;
        body.calculated_price = parseFloat(((l * b * h / 1000000) * selectedVariante.price).toFixed(4));
    } else if (pm === "per_cubic_deci_meter") {
        const l = parseFloat(document.getElementById("kat-laenge").value);
        const b = parseFloat(document.getElementById("kat-breite").value);
        const h = parseFloat(document.getElementById("kat-hoehe").value);
        if ([l, b, h].some((v) => isNaN(v) || v <= 0)) { alert("Bitte alle Maße eingeben."); return; }
        body.laenge_cm = l;
        body.breite_cm = b;
        body.hoehe_cm = h;
        body.calculated_price = parseFloat(((l * b * h / 1000) * selectedVariante.price).toFixed(4));
    } else if (pm === "per_volume_m3") {
        const l = parseFloat(document.getElementById("kat-laenge").value);
        const b = parseFloat(document.getElementById("kat-breite").value);
        const h = parseFloat(document.getElementById("kat-hoehe").value);
        if ([l, b, h].some((v) => isNaN(v) || v <= 0)) { alert("Bitte alle Maße eingeben."); return; }
        body.laenge_cm = l;
        body.breite_cm = b;
        body.hoehe_cm = h;
        body.calculated_price = parseFloat(((l * b * h / 1000000) * selectedVariante.price).toFixed(4));
    } else if (pm === "per_area_m2") {
        const l = parseFloat(document.getElementById("kat-area-laenge").value);
        const b = parseFloat(document.getElementById("kat-area-breite").value);
        if ([l, b].some((v) => isNaN(v) || v <= 0)) { alert("Bitte Länge und Breite eingeben."); return; }
        body.laenge_cm = l;
        body.breite_cm = b;
        body.calculated_price = parseFloat(((l * b / 10000) * selectedVariante.price).toFixed(4));
    } else if (pm === "per_area_dm2") {
        const l = parseFloat(document.getElementById("kat-area-laenge").value);
        const b = parseFloat(document.getElementById("kat-area-breite").value);
        if ([l, b].some((v) => isNaN(v) || v <= 0)) { alert("Bitte Länge und Breite eingeben."); return; }
        body.laenge_cm = l;
        body.breite_cm = b;
        body.calculated_price = parseFloat(((l * b / 100) * selectedVariante.price).toFixed(4));
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
        closeMaterialModal();
        await loadLaufzettel();
    } else {
        const err = await res.json();
        alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen"));
    }
});

// Delete material
async function deleteMaterial(matId) {
    if (!confirm('Möchtest du dieses Material wirklich löschen?')) return;

    try {
        const response = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/material/${matId}`, {
            method: 'DELETE',
        });

        if (response.ok) {
            await loadLaufzettel();
        } else {
            alert('Fehler beim Löschen des Materials');
        }
    } catch (e) {
        alert('Netzwerkfehler. Bitte versuche es erneut.');
    }
}

// Mode toggle
function setMatMode(mode) {
    const freitextBtn = document.getElementById('mode-freitext-btn');
    const katalogBtn = document.getElementById('mode-katalog-btn');
    const freitextFields = document.getElementById('freitext-fields');
    const katalogFields = document.getElementById('katalog-fields');

    if (mode === 'freitext') {
        freitextBtn.classList.add('active');
        katalogBtn.classList.remove('active');
        freitextFields.classList.remove('hidden');
        freitextFields.style.display = 'block';
        katalogFields.classList.add('hidden');
        katalogFields.style.display = 'none';
    } else {
        katalogBtn.classList.add('active');
        freitextBtn.classList.remove('active');
        katalogFields.classList.remove('hidden');
        katalogFields.style.display = 'block';
        freitextFields.classList.add('hidden');
        freitextFields.style.display = 'none';
        loadCatalogData();
    }
}

// Load catalog data
async function loadCatalogData() {
    try {
        const response = await fetch('/api/katalog');
        if (response.ok) {
            katalog = await response.json();
            const select = document.getElementById('kat-select-location');
            select.innerHTML = '<option value="">-- Standort wählen --</option>';
            katalog.forEach(loc => {
                const opt = document.createElement('option');
                opt.value = loc.id;
                opt.textContent = loc.name;
                select.appendChild(opt);
            });
        }
    } catch (e) {
        console.error('Failed to load catalog');
    }
}

// Catalog change handlers
function onKatLocationChange() {
    const locId = parseInt(document.getElementById('kat-select-location').value);
    const katSel = document.getElementById('kat-select-kategorie');
    const varSel = document.getElementById('kat-select-variante');

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
        (loc.kategorien || []).map((k) => `<option value="${k.id}">${esc(k.name)}</option>`).join('');
    katSel.disabled = false;
}

function onKatKategorieChange() {
    const locId = parseInt(document.getElementById('kat-select-location').value);
    const katId = parseInt(document.getElementById('kat-select-kategorie').value);
    const ukatSel = document.getElementById('kat-select-unterkategorie');
    const varSel = document.getElementById('kat-select-variante');

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
    const kat = (loc && loc.kategorien) ? loc.kategorien.find((k) => k.id === katId) : undefined;
    if (!kat) return;

    ukatSel.innerHTML = '<option value="">-- Unterkategorie wählen --</option>' +
        (kat.unterkategorien || []).map((u) => `<option value="${u.id}">${esc(u.name)}</option>`).join('');
    ukatSel.disabled = false;
}

function onKatUnterkategorieChange() {
    const locId = parseInt(document.getElementById('kat-select-location').value);
    const katId = parseInt(document.getElementById('kat-select-kategorie').value);
    const ukatId = parseInt(document.getElementById('kat-select-unterkategorie').value);
    const varSel = document.getElementById('kat-select-variante');

    varSel.innerHTML = '<option value="">-- Variante wählen --</option>';
    varSel.disabled = true;
    selectedVariante = null;
    selectedKategorie = null;
    hideKatInputFields();
    hidePricePreview();

    if (!ukatId) return;
    const loc = katalog.find((l) => l.id === locId);
    const kat = (loc && loc.kategorien) ? loc.kategorien.find((k) => k.id === katId) : undefined;
    const ukat = (kat && kat.unterkategorien) ? kat.unterkategorien.find((u) => u.id === ukatId) : undefined;
    if (!ukat) return;

    selectedKategorie = ukat;  // selectedKategorie now holds the unterkategorie
    const pm = ukat.pricing_model;
    const suffix = pm === "per_gram" ? "/gr"
        : pm === "per_kilogram" ? "/kg"
        : pm === "per_volume_cm3" ? "/cm³"
        : pm === "per_volume_l" ? "/L"
        : pm === "per_cubic_meter" ? "/m³"
        : pm === "per_cubic_deci_meter" ? "/dm³"
        : pm === "per_volume_m3" ? "/m³"
        : pm === "per_area_m2" ? "/m²"
        : pm === "per_area_dm2" ? "/dm²"
        : pm === "per_minute" ? "/min"
        : `/${ukat.unit || "Stück"}`;
    varSel.innerHTML = '<option value="">-- Variante wählen --</option>' +
        (ukat.varianten || []).map((v) => `<option value="${v.id}">${esc(v.name)} (${v.price.toFixed(4)} €${suffix})</option>`).join('');
    varSel.disabled = false;
    // Don't show input fields until a variant is selected, since pricing models are now on variants
    hideKatInputFields();
}

function onKatVarianteChange() {
    const varId = parseInt(document.getElementById('kat-select-variante').value);
    hidePricePreview();
    if (!varId || !selectedKategorie) { selectedVariante = null; return; }
    selectedVariante = (selectedKategorie.varianten ? selectedKategorie.varianten.find((v) => v.id === varId) : null) || null;
    if (selectedVariante) {
        showKatInputFields(selectedVariante.pricing_model || 'per_unit', selectedVariante.unit);
    }
    recalcPrice();
}

function showKatInputFields(pricingModel, unit) {
    const isVolume = pricingModel === 'per_volume_cm3' || pricingModel === 'per_cubic_meter' || pricingModel === 'per_cubic_deci_meter' || pricingModel === 'per_volume_m3';
    const isWeight = pricingModel === 'per_gram' || pricingModel === 'per_kilogram';
    const isArea = pricingModel === 'per_area_m2' || pricingModel === 'per_area_dm2';

    // Use both inline styles and class manipulation to ensure visibility
    const gramEl = document.getElementById('kat-fields-gram');
    const volumeEl = document.getElementById('kat-fields-volume');
    const areaEl = document.getElementById('kat-fields-area');
    const minuteEl = document.getElementById('kat-fields-minute');
    const unitEl = document.getElementById('kat-fields-unit');

    // per_volume_l also uses the single "Menge" field (volume in liters)
    const usesGramField = isWeight || pricingModel === 'per_volume_l';

    // First remove hidden class, then set display style
    if (usesGramField) {
        gramEl.classList.remove('hidden');
        gramEl.style.display = 'block';
        gramEl.style.setProperty('display', 'block', 'important');
    } else {
        gramEl.classList.add('hidden');
        gramEl.style.display = 'none';
    }

    if (isVolume) {
        volumeEl.classList.remove('hidden');
        volumeEl.style.display = 'block';
        volumeEl.style.setProperty('display', 'block', 'important');
    } else {
        volumeEl.classList.add('hidden');
        volumeEl.style.display = 'none';
    }

    if (isArea) {
        areaEl.classList.remove('hidden');
        areaEl.style.display = 'block';
        areaEl.style.setProperty('display', 'block', 'important');
    } else {
        areaEl.classList.add('hidden');
        areaEl.style.display = 'none';
    }

    if (pricingModel === 'per_minute') {
        minuteEl.classList.remove('hidden');
        minuteEl.style.display = 'block';
        minuteEl.style.setProperty('display', 'block', 'important');
    } else {
        minuteEl.classList.add('hidden');
        minuteEl.style.display = 'none';
    }

    if (pricingModel === 'per_unit') {
        unitEl.classList.remove('hidden');
        unitEl.style.display = 'block';
        unitEl.style.setProperty('display', 'block', 'important');
    } else {
        unitEl.classList.add('hidden');
        unitEl.style.display = 'none';
    }

    const unitLabel = unit ? `(${unit})`
        : pricingModel === 'per_kilogram' ? '(kg)'
        : pricingModel === 'per_gram' ? '(g)'
        : pricingModel === 'per_cubic_meter' ? '(m³)'
        : pricingModel === 'per_cubic_deci_meter' ? '(dm³)'
        : pricingModel === 'per_volume_m3' ? '(m³)'
        : pricingModel === 'per_area_m2' ? '(m²)'
        : pricingModel === 'per_area_dm2' ? '(dm²)'
        : pricingModel === 'per_minute' ? '(min)'
        : pricingModel === 'per_volume_l' ? '(L)'
        : '';
    document.getElementById('kat-gram-label').textContent = unitLabel;
    document.getElementById('kat-unit-label').textContent = unitLabel;
    ['kat-menge-gram', 'kat-menge-minute', 'kat-menge-unit', 'kat-laenge', 'kat-breite', 'kat-hoehe', 'kat-area-laenge', 'kat-area-breite'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.oninput = recalcPrice;
    });
}

function hideKatInputFields() {
    ['kat-fields-gram', 'kat-fields-volume', 'kat-fields-area', 'kat-fields-minute', 'kat-fields-unit'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.add('hidden');
            el.style.display = 'none';
            el.style.removeProperty('display');
        }
    });
}

function hidePricePreview() {
    document.getElementById('price-preview').classList.add('hidden');
}

function showPricePreview(price) {
    document.getElementById('price-value').textContent = `${price.toFixed(2)} €`;
    document.getElementById('price-preview').classList.remove('hidden');
}

function recalcPrice() {
    if (!selectedVariante || !selectedKategorie) { hidePricePreview(); return; }
    const pm = selectedVariante.pricing_model || 'per_unit';
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
            price = (l * b * h / 1000000) * selectedVariante.price;
        }
    } else if (pm === "per_cubic_deci_meter") {
        const l = parseFloat(document.getElementById("kat-laenge").value);
        const b = parseFloat(document.getElementById("kat-breite").value);
        const h = parseFloat(document.getElementById("kat-hoehe").value);
        if (!isNaN(l) && !isNaN(b) && !isNaN(h) && l > 0 && b > 0 && h > 0) {
            price = (l * b * h / 1000) * selectedVariante.price;
        }
    } else if (pm === "per_volume_m3") {
        const l = parseFloat(document.getElementById("kat-laenge").value);
        const b = parseFloat(document.getElementById("kat-breite").value);
        const h = parseFloat(document.getElementById("kat-hoehe").value);
        if (!isNaN(l) && !isNaN(b) && !isNaN(h) && l > 0 && b > 0 && h > 0) {
            price = (l * b * h / 1000000) * selectedVariante.price;
        }
    } else if (pm === "per_area_m2") {
        const l = parseFloat(document.getElementById("kat-area-laenge").value);
        const b = parseFloat(document.getElementById("kat-area-breite").value);
        if (!isNaN(l) && !isNaN(b) && l > 0 && b > 0) {
            price = (l * b / 10000) * selectedVariante.price;
        }
    } else if (pm === "per_area_dm2") {
        const l = parseFloat(document.getElementById("kat-area-laenge").value);
        const b = parseFloat(document.getElementById("kat-area-breite").value);
        if (!isNaN(l) && !isNaN(b) && l > 0 && b > 0) {
            price = (l * b / 100) * selectedVariante.price;
        }
    } else if (pm === "per_minute") {
        const menge = parseFloat(document.getElementById("kat-menge-minute").value);
        if (!isNaN(menge) && menge > 0) price = menge * selectedVariante.price;
    } else if (pm === "per_unit") {
        const menge = parseFloat(document.getElementById("kat-menge-unit").value);
        if (!isNaN(menge) && menge > 0) price = menge * selectedVariante.price;
    }

    if (price !== null) {
        showPricePreview(price);
    } else {
        hidePricePreview();
    }
}

// Spende modal
function openSpendeModal() {
    document.getElementById('spende-form').reset();
    document.getElementById('aufrunden-group').style.display = 'none';
    document.getElementById('direct-amount-group').style.display = 'block';
    document.getElementById('spende-modal').classList.remove('hidden');
}

function openAufrundenModal() {
    document.getElementById('spende-form').reset();
    document.getElementById('aufrunden-group').style.display = 'block';
    document.getElementById('direct-amount-group').style.display = 'none';
    document.getElementById('spende-modal').classList.remove('hidden');
    const currentTotal = getCurrentTotal();
    document.getElementById('current-total').textContent = currentTotal.toFixed(2);
    const nextRound = Math.ceil(currentTotal);
    document.getElementById('field-spende-aufrunden-amount').value = nextRound.toFixed(2);
    updateAufrundenDiff();
    document.getElementById('field-spende-aufrunden-amount').focus();
}

function closeSpendeModal() {
    document.getElementById('spende-modal').classList.add('hidden');
}

function getCurrentTotal() {
    const materials = window.MATERIALS_DATA || [];
    return materials.reduce((sum, m) => sum + (m.calculated_price || 0), 0);
}

function updateAufrundenDiff() {
    const target = parseFloat(document.getElementById('field-spende-aufrunden-amount').value);
    const currentTotal = getCurrentTotal();
    if (!isNaN(target) && target > currentTotal) {
        const diff = target - currentTotal;
        document.getElementById('aufrunden-diff').textContent = diff.toFixed(2);
    } else {
        document.getElementById('aufrunden-diff').textContent = '–';
    }
}

async function submitSpendeForm(e) {
    e.preventDefault();

    const name = document.getElementById('field-spende-name').value || 'Spende';
    const isAufrundenMode = document.getElementById('aufrunden-group').style.display !== 'none';
    let amount;

    if (isAufrundenMode) {
        const target = parseFloat(document.getElementById('field-spende-aufrunden-amount').value);
        const currentTotal = getCurrentTotal();
        if (isNaN(target) || target <= currentTotal) {
            alert('Bitte einen Betrag eingeben, der höher als die aktuelle Summe ist.');
            return;
        }
        amount = target - currentTotal;
    } else {
        amount = parseFloat(document.getElementById('field-spende-amount').value);
        if (isNaN(amount) || amount <= 0) {
            alert('Bitte einen gültigen Betrag eingeben.');
            return;
        }
    }

    const body = {
        name: name,
        calculated_price: amount,
        tax_rate: 0, // Spende is tax-free
        is_spende: true,
    };

    try {
        const response = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/material`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (response.ok) {
            closeSpendeModal();
            await loadLaufzettel();
        } else {
            const error = await response.json();
            alert('Fehler: ' + (error.detail || 'Spende konnte nicht erfasst werden'));
        }
    } catch (e) {
        alert('Netzwerkfehler. Bitte versuche es erneut.');
    }
}

// Event listeners
document.getElementById('guest-logout-btn').addEventListener('click', guestLogout);
document.getElementById('add-material-btn').addEventListener('click', openMaterialModal);
document.getElementById('modal-close').addEventListener('click', closeMaterialModal);
document.getElementById('modal-overlay').addEventListener('click', closeMaterialModal);
document.getElementById('cancel-mat-btn').addEventListener('click', closeMaterialModal);

document.getElementById('add-spende-btn').addEventListener('click', openSpendeModal);
document.getElementById('add-aufrunden-btn').addEventListener('click', openAufrundenModal);
document.getElementById('spende-modal-close').addEventListener('click', closeSpendeModal);
document.getElementById('spende-overlay').addEventListener('click', closeSpendeModal);
document.getElementById('spende-cancel').addEventListener('click', closeSpendeModal);
document.getElementById('spende-form').addEventListener('submit', submitSpendeForm);
document.getElementById('field-spende-aufrunden-amount').addEventListener('input', updateAufrundenDiff);

// Initialize
// Load catalog first, then render materials
loadCatalogData().then(() => {
    loadLaufzettel();
});

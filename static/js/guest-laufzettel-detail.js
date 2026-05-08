// Guest Laufzettel Detail JavaScript
// Simplified version of laufzettel-detail.js without payment functionality

let laufzettelData = null;
let allMaterials = [];
let katalog = [];
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

    tbody.innerHTML = allMaterials.map((mat, index) => {
        const mengeStr = formatMenge(mat);
        const priceStr = mat.calculated_price ? `${mat.calculated_price.toFixed(2)} €` : '-';
        return `
            <tr>
                <td>${index + 1}</td>
                <td>${esc(mat.name)}</td>
                <td>${mengeStr}</td>
                <td>${esc(mat.unit || '-')}</td>
                <td>${mat.calculated_price ? calculateUnitPrice(mat).toFixed(4) : '-'}</td>
                <td>${priceStr}</td>
                <td class="actions">
                    <button class="btn btn-sm btn-secondary" onclick="editMaterial(${mat.id})">Bearbeiten</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteMaterial(${mat.id})">Löschen</button>
                </td>
            </tr>
        `;
    }).join('');

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
function formatMenge(mat) {
    if (mat.laenge_cm && mat.breite_cm && mat.hoehe_cm) {
        return `${mat.laenge_cm} × ${mat.breite_cm} × ${mat.hoehe_cm} cm`;
    }
    if (mat.laenge_cm && mat.breite_cm) {
        return `${mat.laenge_cm} × ${mat.breite_cm} cm`;
    }
    return mat.menge !== null ? mat.menge : '-';
}

// Calculate unit price
function calculateUnitPrice(mat) {
    if (!mat.calculated_price || !mat.menge) return 0;
    return mat.calculated_price / mat.menge;
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

// Open material modal
function openMaterialModal() {
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

    document.getElementById('edit-material-id').value = mat.id;
    document.getElementById('edit-mat-variante-id').value = mat.variante_id || '';
    document.getElementById('modal-title').textContent = 'Material bearbeiten';

    if (mat.variante_id) {
        // Load from catalog
        setMatMode('katalog');
        // TODO: Load catalog data and select appropriate options
    } else {
        // Freitext mode
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

// Submit material form
async function submitMaterialForm(e) {
    e.preventDefault();

    const editId = document.getElementById('edit-material-id').value;
    const mode = document.getElementById('katalog-fields').classList.contains('hidden') ? 'freitext' : 'katalog';

    let body = {};

    if (mode === 'freitext') {
        body = {
            name: document.getElementById('field-mat-name').value,
            menge: document.getElementById('field-mat-menge').value ? parseFloat(document.getElementById('field-mat-menge').value) : null,
            unit: document.getElementById('field-mat-unit').value || null,
            calculated_price: document.getElementById('field-mat-total-price').value ? parseFloat(document.getElementById('field-mat-total-price').value) : null,
            tax_rate: parseFloat(document.getElementById('field-mat-tax-rate').value),
        };
    } else {
        // Katalog mode
        body = {
            variante_id: document.getElementById('edit-mat-variante-id').value ? parseInt(document.getElementById('edit-mat-variante-id').value) : null,
            calculated_price: document.getElementById('price-value').textContent ? parseFloat(document.getElementById('price-value').textContent.replace(' €', '')) : null,
            tax_rate: 19, // Default from catalog
        };

        // Add quantity measurements based on pricing model
        if (selectedVariante) {
            const pm = selectedVariante.pricing_model;
            if (pm === 'per_gram' || pm === 'per_kilogram') {
                body.menge = parseFloat(document.getElementById('kat-menge-gram').value) || null;
            } else if (pm === 'per_minute') {
                body.menge = parseFloat(document.getElementById('kat-menge-minute').value) || null;
            } else if (pm === 'per_unit') {
                body.menge = parseFloat(document.getElementById('kat-menge-unit').value) || null;
            } else if (pm.includes('volume')) {
                body.laenge_cm = parseFloat(document.getElementById('kat-laenge').value) || null;
                body.breite_cm = parseFloat(document.getElementById('kat-breite').value) || null;
                body.hoehe_cm = parseFloat(document.getElementById('kat-hoehe').value) || null;
            } else if (pm.includes('area')) {
                body.laenge_cm = parseFloat(document.getElementById('kat-area-laenge').value) || null;
                body.breite_cm = parseFloat(document.getElementById('kat-area-breite').value) || null;
            }
        }
    }

    try {
        let response;
        if (editId) {
            response = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/material/${editId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
        } else {
            response = await fetch(`/api/laufzettel/${LAUFZETTEL_ID}/material`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
        }

        if (response.ok) {
            closeMaterialModal();
            await loadLaufzettel();
        } else {
            const error = await response.json();
            alert('Fehler: ' + (error.detail || 'Material konnte nicht gespeichert werden'));
        }
    } catch (e) {
        alert('Netzwerkfehler. Bitte versuche es erneut.');
    }
}

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

    selectedKategorie = ukat;
    varSel.innerHTML = '<option value="">-- Variante wählen --</option>' +
        (ukat.varianten || []).map((v) => `<option value="${v.id}">${esc(v.name)}</option>`).join('');
    varSel.disabled = false;
}

function onKatVarianteChange() {
    const varId = parseInt(document.getElementById('kat-select-variante').value);
    hidePricePreview();
    if (!varId || !selectedKategorie) {
        selectedVariante = null;
        hideKatInputFields();
        return;
    }
    selectedVariante = (selectedKategorie.varianten ? selectedKategorie.varianten.find((v) => v.id === varId) : null) || null;
    console.log('Variant selected:', selectedVariante);
    if (selectedVariante) {
        console.log('Showing input fields for pricing model:', selectedVariante.pricing_model, 'unit:', selectedVariante.unit);
        showKatInputFields(selectedVariante.pricing_model, selectedVariante.unit);
        recalcPrice();
    } else {
        console.log('No variant found, hiding input fields');
        hideKatInputFields();
    }
}

function showKatInputFields(pricingModel, unit) {
    console.log('showKatInputFields called with pricingModel:', pricingModel, 'unit:', unit);
    const isVolume = pricingModel === 'per_volume_cm3' || pricingModel === 'per_volume_l' || pricingModel === 'per_cubic_meter' || pricingModel === 'per_cubic_deci_meter' || pricingModel === 'per_volume_m3';
    const isWeight = pricingModel === 'per_gram' || pricingModel === 'per_kilogram';
    const isArea = pricingModel === 'per_area_m2' || pricingModel === 'per_area_dm2';

    console.log('isVolume:', isVolume, 'isWeight:', isWeight, 'isArea:', isArea);

    // Use both inline styles and class manipulation to ensure visibility
    const gramEl = document.getElementById('kat-fields-gram');
    const volumeEl = document.getElementById('kat-fields-volume');
    const areaEl = document.getElementById('kat-fields-area');
    const minuteEl = document.getElementById('kat-fields-minute');
    const unitEl = document.getElementById('kat-fields-unit');

    console.log('Elements found:', {
        gramEl: !!gramEl,
        volumeEl: !!volumeEl,
        areaEl: !!areaEl,
        minuteEl: !!minuteEl,
        unitEl: !!unitEl
    });

    // First remove hidden class, then set display style
    if (isWeight) {
        gramEl.classList.remove('hidden');
        gramEl.style.display = 'block';
        gramEl.style.setProperty('display', 'block', 'important');
    } else {
        gramEl.classList.add('hidden');
        gramEl.style.display = 'none';
    }
    console.log('gramEl after - display:', gramEl.style.display, 'classList:', gramEl.classList.toString());

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

    const unitLabel = unit ? `(${unit})` : (pricingModel === 'per_kilogram' ? '(kg)' : pricingModel === 'per_gram' ? '(g)' : '');
    document.getElementById('kat-gram-label').textContent = unitLabel;
    document.getElementById('kat-unit-label').textContent = unitLabel;
    ['kat-menge-gram', 'kat-menge-minute', 'kat-menge-unit', 'kat-laenge', 'kat-breite', 'kat-hoehe', 'kat-area-laenge', 'kat-area-breite'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.oninput = recalcPrice;
    });
}

function hideKatInputFields() {
    console.log('hideKatInputFields called');
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
    if (!selectedVariante) return;
    let menge = 0;
    const pm = selectedVariante.pricing_model;

    if (pm === 'per_gram' || pm === 'per_kilogram' || pm === 'per_minute' || pm === 'per_unit') {
        menge = parseFloat(document.getElementById('kat-menge-' + (pm === 'per_gram' || pm === 'per_kilogram' ? 'gram' : pm === 'per_minute' ? 'minute' : 'unit')).value) || 0;
        if (pm === 'per_kilogram') menge = menge * 1000;
    } else if (pm.includes('volume')) {
        const l = parseFloat(document.getElementById('kat-laenge').value) || 0;
        const b = parseFloat(document.getElementById('kat-breite').value) || 0;
        const h = parseFloat(document.getElementById('kat-hoehe').value) || 0;
        menge = l * b * h;
        if (pm === 'per_volume_l') menge = menge / 1000;
        else if (pm === 'per_cubic_meter') menge = menge / 1000000;
        else if (pm === 'per_cubic_deci_meter') menge = menge / 1000;
    } else if (pm.includes('area')) {
        const l = parseFloat(document.getElementById('kat-area-laenge').value) || 0;
        const b = parseFloat(document.getElementById('kat-area-breite').value) || 0;
        menge = l * b;
        if (pm === 'per_area_m2') menge = menge / 10000;
    }

    const price = menge * selectedVariante.price;
    showPricePreview(price);
}

// Spende modal
function openSpendeModal() {
    document.getElementById('spende-form').reset();
    document.getElementById('spende-modal').classList.remove('hidden');
}

function closeSpendeModal() {
    document.getElementById('spende-modal').classList.add('hidden');
}

async function submitSpendeForm(e) {
    e.preventDefault();

    const body = {
        name: document.getElementById('field-spende-name').value,
        calculated_price: parseFloat(document.getElementById('field-spende-amount').value),
        tax_rate: 0, // Spende is tax-free
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
document.getElementById('add-material-btn').addEventListener('click', openMaterialModal);
document.getElementById('modal-close').addEventListener('click', closeMaterialModal);
document.getElementById('modal-overlay').addEventListener('click', closeMaterialModal);
document.getElementById('cancel-mat-btn').addEventListener('click', closeMaterialModal);
document.getElementById('material-form').addEventListener('submit', submitMaterialForm);

document.getElementById('add-spende-btn').addEventListener('click', openSpendeModal);
document.getElementById('spende-modal-close').addEventListener('click', closeSpendeModal);
document.getElementById('spende-overlay').addEventListener('click', closeSpendeModal);
document.getElementById('spende-cancel').addEventListener('click', closeSpendeModal);
document.getElementById('spende-form').addEventListener('submit', submitSpendeForm);

// Initialize
loadLaufzettel();

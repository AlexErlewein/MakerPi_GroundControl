// Buchhaltung - Accounting overview

let currentPeriod = 'month';
let currentReferenceDate = null; // ISO date string or null = current period

function formatEuro(val) {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val || 0);
}

function formatDate(iso) {
    if (!iso) return '–';
    return new Date(iso).toLocaleDateString('de-DE');
}

function escHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Period dropdown builders ──────────────────────────────────────────────────

function buildYearOptions() {
    const currentYear = new Date().getFullYear();
    const options = [];
    for (let y = currentYear; y >= currentYear - 4; y--) {
        options.push({ label: String(y), value: `${y}-06-15` });
    }
    return options;
}

function buildMonthOptions() {
    const now = new Date();
    const options = [];
    for (let i = 0; i < 24; i++) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const label = d.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' });
        const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
        options.push({ label, value });
    }
    return options;
}

function buildWeekOptions() {
    const now = new Date();
    const options = [];
    for (let i = 0; i < 16; i++) {
        const d = new Date(now);
        d.setDate(now.getDate() - i * 7);
        // Monday of that week
        const monday = new Date(d);
        monday.setDate(d.getDate() - d.getDay() + (d.getDay() === 0 ? -6 : 1));
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);

        // ISO week number
        const jan4 = new Date(monday.getFullYear(), 0, 4);
        const weekNum = Math.ceil(((monday - jan4) / 86400000 + jan4.getDay() + 1) / 7);

        const fmt = (dt) => dt.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
        const label = `KW ${weekNum} (${fmt(monday)} – ${fmt(sunday)})`;
        const value = `${monday.getFullYear()}-${String(monday.getMonth() + 1).padStart(2, '0')}-${String(monday.getDate()).padStart(2, '0')}`;
        options.push({ label, value });
    }
    return options;
}

function updatePeriodDropdown() {
    const select = document.getElementById('period-select');
    let options = [];
    if (currentPeriod === 'year')  options = buildYearOptions();
    if (currentPeriod === 'month') options = buildMonthOptions();
    if (currentPeriod === 'week')  options = buildWeekOptions();

    select.innerHTML = options.map((o, i) =>
        `<option value="${o.value}"${i === 0 ? ' selected' : ''}>${escHtml(o.label)}</option>`
    ).join('');
    // Default to first option (= current period)
    currentReferenceDate = options[0]?.value || null;
}

// ── Load & render ─────────────────────────────────────────────────────────────

async function loadSummary() {
    try {
        let url = `/api/buchhaltung/summary?period=${currentPeriod}`;
        if (currentReferenceDate) url += `&reference_date=${currentReferenceDate}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to load summary');
        const data = await res.json();

        document.getElementById('total-revenue').textContent = formatEuro(data.total);
        document.getElementById('material-revenue').textContent = formatEuro(data.material_total);
        document.getElementById('spende-revenue').textContent = formatEuro(data.spende_total);

        const tt = data.tax_totals || {};
        document.getElementById('tax-revenue-19').textContent    = formatEuro(tt['19']     || 0);
        document.getElementById('tax-revenue-7').textContent     = formatEuro(tt['7']      || 0);
        document.getElementById('tax-revenue-0').textContent     = formatEuro(tt['0']      || 0);
        document.getElementById('tax-revenue-spende').textContent = formatEuro(tt['spende'] || 0);

        const tg = data.tax_groups || {};
        renderVariantTable(tg['19']     || [], 'variant-tbody-19');
        renderVariantTable(tg['7']      || [], 'variant-tbody-7');
        renderVariantTable(tg['0']      || [], 'variant-tbody-0');
        renderVariantTable(tg['spende'] || [], 'variant-tbody-spende');
        renderSpendeTable(data.spenden || []);
    } catch (e) {
        console.error('Error loading summary:', e);
    }
}

function renderVariantTable(variants, tbodyId) {
    const tbody = document.getElementById(tbodyId);
    if (!variants.length) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="3">Keine Einträge im gewählten Zeitraum.</td></tr>';
        return;
    }
    tbody.innerHTML = variants.map(v => {
        const menge = v.units != null ? `${v.units.toFixed(2)} ${v.unit || ''}`.trim() : '–';
        return `<tr>
            <td>${escHtml(v.name)}</td>
            <td>${escHtml(menge)}</td>
            <td>${formatEuro(v.revenue)}</td>
        </tr>`;
    }).join('');
}

function renderSpendeTable(spenden) {
    const tbody = document.getElementById('spende-tbody');
    if (!spenden.length) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Keine Spenden im gewählten Zeitraum.</td></tr>';
        return;
    }
    tbody.innerHTML = spenden.map(s => `<tr>
        <td>${formatDate(s.date)}</td>
        <td>${formatEuro(s.amount)}</td>
        <td>${escHtml(s.donor_name || 'Anonym')}</td>
        <td>${escHtml(s.notes || '–')}</td>
        <td><button class="btn btn-sm btn-danger" onclick="deleteSpende(${s.id})">Löschen</button></td>
    </tr>`).join('');
}

async function deleteSpende(id) {
    if (!confirm('Spende wirklich löschen?')) return;
    try {
        const res = await fetch(`/api/buchhaltung/spende/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Delete failed');
        await loadSummary();
    } catch (e) {
        alert('Fehler beim Löschen: ' + e.message);
    }
}

// ── Period toggle ─────────────────────────────────────────────────────────────

document.querySelectorAll('.period-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentPeriod = btn.dataset.period;
        updatePeriodDropdown();
        loadSummary();
    });
});

document.getElementById('period-select').addEventListener('change', (e) => {
    currentReferenceDate = e.target.value;
    loadSummary();
});

// ── Spende modal ──────────────────────────────────────────────────────────────

const modal = document.getElementById('spende-modal');
document.getElementById('add-spende-btn').addEventListener('click', () => {
    document.getElementById('spende-date').value = new Date().toISOString().slice(0, 10);
    modal.classList.add('open');
});
document.getElementById('spende-cancel-btn').addEventListener('click', () => modal.classList.remove('open'));
modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('open'); });

document.getElementById('spende-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const amount = parseFloat(document.getElementById('spende-amount').value);
    const donor_name = document.getElementById('spende-donor').value.trim() || null;
    const date = document.getElementById('spende-date').value || null;
    const notes = document.getElementById('spende-notes').value.trim() || null;
    if (!amount || amount <= 0) { alert('Bitte einen gültigen Betrag eingeben.'); return; }
    try {
        const res = await fetch('/api/buchhaltung/spende', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, donor_name, date, notes }),
        });
        if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Fehler beim Speichern'); }
        modal.classList.remove('open');
        e.target.reset();
        await loadSummary();
    } catch (err) {
        alert('Fehler: ' + err.message);
    }
});

// ── Init ──────────────────────────────────────────────────────────────────────

function filterRows(inputId, tbodyId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const needle = input.value.trim().toLowerCase();
    document.querySelectorAll(`#${tbodyId} tr`).forEach(tr => {
        tr.style.display = !needle || tr.textContent.toLowerCase().includes(needle) ? '' : 'none';
    });
}

const variantSearch = document.getElementById('variant-search');
const spendeSearch = document.getElementById('spende-search');
if (variantSearch) variantSearch.addEventListener('input', () => {
    ['variant-tbody-19', 'variant-tbody-7', 'variant-tbody-0', 'variant-tbody-spende'].forEach(id => {
        const needle = variantSearch.value.trim().toLowerCase();
        document.querySelectorAll(`#${id} tr`).forEach(tr => {
            tr.style.display = !needle || tr.textContent.toLowerCase().includes(needle) ? '' : 'none';
        });
    });
});
if (spendeSearch) spendeSearch.addEventListener('input', () => filterRows('spende-search', 'spende-tbody'));

updatePeriodDropdown();
loadSummary();

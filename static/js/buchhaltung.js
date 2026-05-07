// Buchhaltung - Accounting overview

let currentPeriod = 'month';

function formatEuro(val) {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val || 0);
}

function formatDate(iso) {
    if (!iso) return '–';
    const d = new Date(iso);
    return d.toLocaleDateString('de-DE');
}

async function loadSummary() {
    try {
        const res = await fetch(`/api/buchhaltung/summary?period=${currentPeriod}`);
        if (!res.ok) throw new Error('Failed to load summary');
        const data = await res.json();

        document.getElementById('total-revenue').textContent = formatEuro(data.total);
        document.getElementById('material-revenue').textContent = formatEuro(data.material_total);
        document.getElementById('spende-revenue').textContent = formatEuro(data.spende_total);

        renderVariantTable(data.by_variant || []);
        renderSpendeTable(data.spenden || []);
    } catch (e) {
        console.error('Error loading summary:', e);
    }
}

function renderVariantTable(variants) {
    const tbody = document.getElementById('variant-tbody');
    if (!variants.length) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="3">Keine Materialverkäufe im gewählten Zeitraum.</td></tr>';
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
        <td><button class="btn-danger" onclick="deleteSpende(${s.id})">Löschen</button></td>
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

function escHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// Period toggle
document.querySelectorAll('.period-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentPeriod = btn.dataset.period;
        loadSummary();
    });
});

// Spende modal
const modal = document.getElementById('spende-modal');
document.getElementById('add-spende-btn').addEventListener('click', () => {
    // Default date to today
    const today = new Date().toISOString().slice(0, 10);
    document.getElementById('spende-date').value = today;
    modal.classList.add('open');
});
document.getElementById('spende-cancel-btn').addEventListener('click', () => {
    modal.classList.remove('open');
});
modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('open');
});

document.getElementById('spende-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const amount = parseFloat(document.getElementById('spende-amount').value);
    const donor_name = document.getElementById('spende-donor').value.trim() || null;
    const date = document.getElementById('spende-date').value || null;
    const notes = document.getElementById('spende-notes').value.trim() || null;

    if (!amount || amount <= 0) {
        alert('Bitte einen gültigen Betrag eingeben.');
        return;
    }

    try {
        const res = await fetch('/api/buchhaltung/spende', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, donor_name, date, notes }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Fehler beim Speichern');
        }
        modal.classList.remove('open');
        e.target.reset();
        await loadSummary();
    } catch (err) {
        alert('Fehler: ' + err.message);
    }
});

// Initial load
loadSummary();

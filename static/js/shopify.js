/* Shopify gift card tracking */

const fmt = (val, currency = 'EUR') =>
    new Intl.NumberFormat('de-DE', { style: 'currency', currency }).format(val);

const fmtDate = (iso) => {
    if (!iso) return '–';
    return new Date(iso).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

async function loadSummary() {
    try {
        const res = await fetch('/api/shopify/gift-cards/summary');
        if (!res.ok) throw new Error(await res.text());
        const d = await res.json();
        document.getElementById('stat-total').textContent = d.total_cards;
        document.getElementById('stat-active').textContent = d.active_cards;
        document.getElementById('stat-issued').textContent = fmt(d.total_issued_eur);
        document.getElementById('stat-outstanding').textContent = fmt(d.total_outstanding_eur);
        document.getElementById('stat-redeemed').textContent = fmt(d.total_redeemed_eur);
    } catch (e) {
        console.error('Summary error:', e);
    }
}

async function loadCards(status = 'enabled') {
    const tbody = document.getElementById('cards-tbody');
    tbody.innerHTML = '<tr class="empty-row"><td colspan="10">Lade Daten...</td></tr>';

    try {
        const res = await fetch(`/api/shopify/gift-cards?status=${status}`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            tbody.innerHTML = `<tr class="empty-row"><td colspan="10" style="color:var(--danger)">Fehler: ${err.detail || res.statusText}</td></tr>`;
            return;
        }
        const { gift_cards: cards } = await res.json();

        if (!cards.length) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="10">Keine Gutscheine gefunden.</td></tr>';
            return;
        }

        tbody.innerHTML = cards.map(c => {
            const redeemed = c.initial_value - c.balance;
            const pct = c.initial_value > 0 ? Math.round((redeemed / c.initial_value) * 100) : 0;
            const statusBadge = c.status === 'enabled'
                ? '<span class="badge badge-active">Aktiv</span>'
                : '<span class="badge badge-disabled">Inaktiv</span>';
            const progressBar = `
                <div class="progress-bar-wrap" title="${pct}% eingelöst">
                    <div class="progress-bar" style="width:${pct}%"></div>
                </div>`;
            const code = c.last_characters ? `****${c.last_characters}` : (c.code || '–');
            return `<tr>
                <td><code>${code}</code></td>
                <td>${fmt(c.initial_value, c.currency)}</td>
                <td>${fmt(c.balance, c.currency)}</td>
                <td>${fmt(redeemed, c.currency)}</td>
                <td>${progressBar}</td>
                <td>${statusBadge}</td>
                <td>${fmtDate(c.created_at)}</td>
                <td>${c.expires_on ? fmtDate(c.expires_on) : '–'}</td>
                <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-secondary)">${c.note || ''}</td>
                <td><button class="btn btn-secondary" style="padding:3px 10px;font-size:0.8rem" onclick="openTxModal(${c.id}, '${code}')">Details</button></td>
            </tr>`;
        }).join('');
    } catch (e) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="10" style="color:var(--danger)">Netzwerkfehler: ${e.message}</td></tr>`;
    }
}

async function openTxModal(cardId, code) {
    const overlay = document.getElementById('tx-modal');
    const title = document.getElementById('tx-modal-title');
    const body = document.getElementById('tx-modal-body');

    title.textContent = `Transaktionen – ${code}`;
    body.innerHTML = '<p style="color:var(--text-secondary)">Lade...</p>';
    overlay.classList.add('open');

    try {
        const res = await fetch(`/api/shopify/gift-cards/${cardId}/transactions`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            body.innerHTML = `<p style="color:var(--danger)">Fehler: ${err.detail}</p>`;
            return;
        }
        const { transactions } = await res.json();

        if (!transactions.length) {
            body.innerHTML = '<p style="color:var(--text-secondary)">Keine Transaktionen vorhanden.</p>';
            return;
        }

        body.innerHTML = transactions.map(t => {
            const kindClass = t.kind === 'credit' ? 'tx-kind-credit' : 'tx-kind-debit';
            const kindLabel = t.kind === 'credit' ? '+ Aufladung' : '– Einlösung';
            const sign = t.kind === 'credit' ? '+' : '-';
            return `<div class="tx-row">
                <span class="${kindClass}">${kindLabel}</span>
                <span class="tx-amount">${sign}${fmt(Math.abs(t.amount))}</span>
                <span class="tx-date">${fmtDate(t.created_at)}</span>
                ${t.note ? `<span class="tx-note">${t.note}</span>` : ''}
            </div>`;
        }).join('');
    } catch (e) {
        body.innerHTML = `<p style="color:var(--danger)">Netzwerkfehler: ${e.message}</p>`;
    }
}

function closeTxModal() {
    document.getElementById('tx-modal').classList.remove('open');
}

document.addEventListener('DOMContentLoaded', () => {
    const filterSelect = document.getElementById('status-filter');
    const refreshBtn = document.getElementById('refresh-btn');
    const txClose = document.getElementById('tx-close');
    const txOverlay = document.getElementById('tx-modal');

    if (!filterSelect) return; // page not configured

    const refresh = () => {
        loadSummary();
        loadCards(filterSelect.value);
    };

    filterSelect.addEventListener('change', () => loadCards(filterSelect.value));
    refreshBtn.addEventListener('click', refresh);
    txClose.addEventListener('click', closeTxModal);
    txOverlay.addEventListener('click', (e) => { if (e.target === txOverlay) closeTxModal(); });

    refresh();
});

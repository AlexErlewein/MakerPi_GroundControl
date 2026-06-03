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
        let { gift_cards: cards } = await res.json();

        const showExhausted = document.getElementById('show-exhausted')?.checked ?? false;
        if (!showExhausted) {
            cards = cards.filter(c => c.balance > 0);
        }

        if (!cards.length) {
            const hint = showExhausted ? '' : ' (aufgebrauchte ausgeblendet)';
            tbody.innerHTML = `<tr class="empty-row"><td colspan="10">Keine Gutscheine gefunden${hint}.</td></tr>`;
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
                <td><button class="btn btn-secondary" style="padding:3px 10px;font-size:0.8rem" onclick="openDetailModal(${c.id}, '${code}')">Details</button></td>
            </tr>`;
        }).join('');
    } catch (e) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="10" style="color:var(--danger)">Netzwerkfehler: ${e.message}</td></tr>`;
    }
    applySearch('shopify-search', '#cards-tbody tr');
}

// ── Detail Modal ────────────────────────────────────────────────────────────

async function openDetailModal(cardId, code) {
    const overlay = document.getElementById('tx-modal');
    const title = document.getElementById('tx-modal-title');
    const body = document.getElementById('tx-modal-body');

    title.textContent = `Gutschein – ${code}`;
    body.innerHTML = '<p style="color:var(--text-secondary)">Lade...</p>';
    overlay.classList.add('open');

    try {
        const res = await fetch(`/api/shopify/gift-cards/${cardId}`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            body.innerHTML = `<p style="color:var(--danger)">Fehler: ${err.detail}</p>`;
            return;
        }
        const card = await res.json();

        body.innerHTML = buildDetailHTML(card);
    } catch (e) {
        body.innerHTML = `<p style="color:var(--danger)">Netzwerkfehler: ${e.message}</p>`;
    }
}

function buildDetailHTML(c) {
    const redeemed = c.initial_value - c.balance;
    let html = '';

    // Info section
    const balanceClass = c.balance <= 0 && c.enabled ? 'color:var(--text-secondary)' : 'color:var(--accent)';
    html += `<div class="detail-section">
        <div class="detail-row"><span class="label">Guthaben</span><span class="value" style="font-size:1.2rem;font-weight:700;${balanceClass}">${fmt(c.balance, c.currency)}</span></div>
        <div class="detail-row"><span class="label">Status</span><span class="value">${c.enabled ? '<span class="badge badge-active">Aktiv</span>' : '<span class="badge badge-disabled">Inaktiv</span>'}</span></div>
        <div class="detail-row"><span class="label">Anfangswert</span><span class="value">${fmt(c.initial_value, c.currency)}</span></div>
        <div class="detail-row"><span class="label">Eingelöst</span><span class="value">${fmt(redeemed, c.currency)}</span></div>
        <div class="detail-row"><span class="label">Erstellt</span><span class="value">${fmtDate(c.created_at)}</span></div>
        ${c.expires_on ? `<div class="detail-row"><span class="label">Ablaufdatum</span><span class="value">${fmtDate(c.expires_on)}</span></div>` : ''}
    </div>`;

    // Customer section
    if (c.customer) {
        html += `<div class="detail-section">
            <h4>Kunde</h4>
            <div class="detail-row"><span class="label">Name</span><span class="value">${c.customer.name}</span></div>
            ${c.customer.email ? `<div class="detail-row"><span class="label">E-Mail</span><span class="value"><a href="mailto:${c.customer.email}" style="color:var(--accent)">${c.customer.email}</a></span></div>` : ''}
        </div>`;
    }

    // Note section
    html += `<div class="detail-section">
        <h4>Notiz</h4>
        <textarea class="note-textarea" id="detail-note" placeholder="Interne Notiz hinzufügen…">${c.note || ''}</textarea>
        <div class="detail-actions">
            <button class="btn-sm primary" id="save-note-btn" onclick="saveNote(${c.id})">Speichern</button>
            <span class="status-msg" id="note-status"></span>
        </div>
    </div>`;

    // Balance adjustment section
    html += `<div class="detail-section">
        <h4>Guthaben anpassen</h4>
        <div class="adjust-row">
            <input type="number" class="adjust-input" id="adjust-amount" step="0.01" min="0.01" placeholder="Betrag">
            <select class="adjust-input" id="adjust-type" style="width:auto">
                <option value="credit">Aufladen (+)</option>
                <option value="debit">Abziehen (−)</option>
            </select>
            <button class="btn-sm" id="adjust-btn" onclick="adjustBalance(${c.id})">Ausführen</button>
            <span class="status-msg" id="adjust-status"></span>
        </div>
    </div>`;

    // Status toggle section
    const toggleLabel = c.enabled ? 'Deaktivieren' : 'Reaktivieren';
    const toggleClass = c.enabled ? 'danger' : '';
    html += `<div class="detail-section">
        <div class="detail-actions">
            <button class="btn-sm ${toggleClass}" onclick="toggleStatus(${c.id})">${toggleLabel}</button>
            <span class="status-msg" id="toggle-status"></span>
        </div>
    </div>`;

    // Transactions section
    html += '<hr class="detail-divider"><div class="detail-section"><h4>Transaktionen</h4>';
    if (c.transactions.length) {
        html += c.transactions.map(t => {
            const isCredit = t.amount > 0;
            const cls = isCredit ? 'tx-kind-credit' : 'tx-kind-debit';
            const label = isCredit ? '+ Aufladung' : '– Einlösung';
            const sign = isCredit ? '+' : '-';
            return `<div class="tx-row">
                <span class="${cls}">${label}</span>
                <span class="tx-amount">${sign}${fmt(Math.abs(t.amount), t.currency)}</span>
                <span class="tx-date">${fmtDate(t.processed_at)}</span>
                ${t.note ? `<span class="tx-note">${t.note}</span>` : ''}
            </div>`;
        }).join('');
    } else {
        html += '<p style="color:var(--text-secondary);font-size:0.9rem">Keine Transaktionen vorhanden.</p>';
    }
    html += '</div>';

    return html;
}

async function saveNote(cardId) {
    const noteEl = document.getElementById('detail-note');
    const statusEl = document.getElementById('note-status');
    const btn = document.getElementById('save-note-btn');
    const note = noteEl.value;

    btn.disabled = true;
    statusEl.textContent = '';
    statusEl.className = 'status-msg';

    try {
        const res = await fetch(`/api/shopify/gift-cards/${cardId}/note`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail);
        }
        statusEl.textContent = 'Gespeichert ✓';
        statusEl.className = 'status-msg ok';
        // Update table note column silently
        loadCards(document.getElementById('status-filter')?.value || 'enabled');
    } catch (e) {
        statusEl.textContent = e.message;
        statusEl.className = 'status-msg err';
    } finally {
        btn.disabled = false;
    }
}

async function adjustBalance(cardId) {
    const amountEl = document.getElementById('adjust-amount');
    const typeEl = document.getElementById('adjust-type');
    const statusEl = document.getElementById('adjust-status');
    const btn = document.getElementById('adjust-btn');
    const amount = parseFloat(amountEl.value);

    if (!amount || amount <= 0) {
        statusEl.textContent = 'Bitte einen gültigen Betrag eingeben';
        statusEl.className = 'status-msg err';
        return;
    }

    const finalAmount = typeEl.value === 'debit' ? -Math.abs(amount) : Math.abs(amount);
    const note = `${typeEl.value === 'credit' ? 'Manuelle Aufladung' : 'Manueller Abzug'} via GroundControl`;

    btn.disabled = true;
    statusEl.textContent = '';
    statusEl.className = 'status-msg';

    if (!confirm(`${typeEl.value === 'credit' ? 'Aufladen' : 'Abziehen'}: ${fmt(Math.abs(amount))} – sicher?`)) {
        btn.disabled = false;
        return;
    }

    try {
        const res = await fetch(`/api/shopify/gift-cards/${cardId}/adjust`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: finalAmount, note }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail);
        }
        statusEl.textContent = `Erfolgreich: ${typeEl.value === 'credit' ? '+' : '−'}${fmt(amount)} ✓`;
        statusEl.className = 'status-msg ok';
        amountEl.value = '';
        // Reload detail and table
        openDetailModal(cardId, document.getElementById('tx-modal-title').textContent.split('– ')[1]?.trim() || '');
    } catch (e) {
        statusEl.textContent = e.message;
        statusEl.className = 'status-msg err';
    } finally {
        btn.disabled = false;
    }
}

async function toggleStatus(cardId) {
    const statusEl = document.getElementById('toggle-status');

    if (!confirm('Status dieses Gutscheins ändern?')) return;

    statusEl.textContent = '';
    statusEl.className = 'status-msg';

    try {
        const res = await fetch(`/api/shopify/gift-cards/${cardId}/toggle`, { method: 'POST' });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail);
        }
        const { disabled } = await res.json();
        statusEl.textContent = disabled ? 'Deaktiviert ✓' : 'Reaktiviert ✓';
        statusEl.className = 'status-msg ok';
        // Reload detail and table
        openDetailModal(cardId, document.getElementById('tx-modal-title').textContent.split('– ')[1]?.trim() || '');
    } catch (e) {
        statusEl.textContent = e.message;
        statusEl.className = 'status-msg err';
    }
}

// ── Physical Gift Card Orders ────────────────────────────────────────────


async function loadPhysicalOrders() {
    const area = document.getElementById('physical-orders-area');
    if (!area) return;

    try {
        const res = await fetch('/api/shopify/physical-product/orders');
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        if (!data.configured) {
            area.innerHTML = '<p style="color:var(--text-secondary)">Nicht konfiguriert. Setze <code>shopify_physical_product_id</code> in config.json.</p>';
            return;
        }
        if (data.error) {
            area.innerHTML = `<p style="color:var(--danger)">Fehler: ${data.error}</p>`;
            return;
        }

        if (!data.orders.length) {
            area.innerHTML = '<p style="color:var(--text-secondary)">Keine Verkäufe für physische Gutscheine gefunden.</p>';
            return;
        }

        const financialBadge = (status) => {
            const map = {
                'PAID': ['Bezahlt', 'financial-paid'],
                'PENDING': ['Ausstehend', 'financial-pending'],
                'REFUNDED': ['Erstattet', 'financial-refunded'],
                'PARTIALLY_REFUNDED': ['Teil-Erstattet', 'financial-pending'],
            };
            const [label, cls] = map[status] || [status, 'financial-pending'];
            return `<span class="financial-badge ${cls}">${label}</span>`;
        };

        const fulfillmentBadge = (status) => {
            const map = {
                'FULFILLED': ['Versandt', 'fulfillment-fulfilled'],
                'UNFULFILLED': ['Offen', 'fulfillment-unfulfilled'],
                'PARTIALLY_FULFILLED': ['Teilweise', 'fulfillment-partial'],
            };
            const [label, cls] = map[status] || [status, 'fulfillment-unfulfilled'];
            return `<span class="financial-badge ${cls}">${label}</span>`;
        };

        let html = `<div class="table-wrap"><table>
            <thead><tr>
                <th>Bestellung</th>
                <th>Datum</th>
                <th>Kunde</th>
                <th>Variante</th>
                <th>Stk</th>
                <th>Bezahlung</th>
                <th>Versand</th>
                <th>Kommentar</th>
                <th></th>
            </tr></thead>
            <tbody>`;

        for (const o of data.orders) {
            const customerDisplay = o.customer.name || '<span style="color:var(--text-secondary)">–</span>';
            const customerEmail = o.customer.email ? ` <a href="mailto:${o.customer.email}" style="color:var(--text-secondary);font-size:0.8rem" title="${o.customer.email}">✉</a>` : '';
            const noteDisplay = o.note
                ? `<span title="${o.note.replace(/"/g, '&quot;')}">${o.note.length > 30 ? o.note.substring(0, 30) + '…' : o.note}</span>`
                : '<span style="color:var(--text-secondary)">–</span>';
            html += `<tr id="order-row-${o.shopify_order_id}">
                <td style="font-weight:600">${o.name}</td>
                <td>${fmtDate(o.created_at)}</td>
                <td>${customerDisplay}${customerEmail}</td>
                <td>${o.variant || '–'}</td>
                <td>${o.quantity}</td>
                <td>${financialBadge(o.financial_status)}</td>
                <td>${fulfillmentBadge(o.fulfillment_status)}</td>
                <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${noteDisplay}</td>
                <td><button class="btn btn-secondary" style="padding:3px 10px;font-size:0.8rem" onclick="openOrderDetailModal('${o.shopify_order_id}', '${o.name}')">Details</button></td>
            </tr>`;
        }

        html += '</tbody></table></div>';
        if (data.has_next) {
            html += '<p style="color:var(--text-secondary);font-size:0.85rem;margin-top:8px">Weitere Bestellungen verfügbar (Pagination nicht implementiert).</p>';
        }

        area.innerHTML = html;
        applySearch('shopify-search', '#physical-orders-area tbody tr');
    } catch (e) {
        area.innerHTML = `<p style="color:var(--danger)">Fehler: ${e.message}</p>`;
    }
}

// ── Physical Order Detail Modal ──────────────────────────────────────────


async function openOrderDetailModal(orderId, orderName) {
    const overlay = document.getElementById('order-modal');
    const title = document.getElementById('order-modal-title');
    const body = document.getElementById('order-modal-body');

    title.textContent = `Bestellung – ${orderName}`;
    body.innerHTML = '<p style="color:var(--text-secondary)">Lade...</p>';
    overlay.classList.add('open');

    try {
        const res = await fetch(`/api/shopify/physical-product/orders/${orderId}`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            body.innerHTML = `<p style="color:var(--danger)">Fehler: ${err.detail}</p>`;
            return;
        }
        const o = await res.json();
        body.innerHTML = buildOrderDetailHTML(o);
    } catch (e) {
        body.innerHTML = `<p style="color:var(--danger)">Netzwerkfehler: ${e.message}</p>`;
    }
}

function buildOrderDetailHTML(o) {
    let html = '';

    // Status badges
    const financialBadge = (status) => {
        const map = {
            'PAID': ['Bezahlt', 'financial-paid'],
            'PENDING': ['Ausstehend', 'financial-pending'],
            'REFUNDED': ['Erstattet', 'financial-refunded'],
        };
        const [label, cls] = map[status] || [status, 'financial-pending'];
        return `<span class="financial-badge ${cls}">${label}</span>`;
    };
    const fulfillmentBadge = (status) => {
        const map = {
            'FULFILLED': ['Versandt/Abgeholt', 'fulfillment-fulfilled'],
            'UNFULFILLED': ['Offen', 'fulfillment-unfulfilled'],
            'PARTIALLY_FULFILLED': ['Teilweise', 'fulfillment-partial'],
        };
        const [label, cls] = map[status] || [status, 'fulfillment-unfulfilled'];
        return `<span class="financial-badge ${cls}">${label}</span>`;
    };

    // Order info
    html += `<div class="detail-section">
        <div class="detail-row"><span class="label">Bestellung</span><span class="value" style="font-weight:700">${o.name}</span></div>
        <div class="detail-row"><span class="label">Erstellt</span><span class="value">${fmtDate(o.created_at)}</span></div>
        <div class="detail-row"><span class="label">Gesamt</span><span class="value">${fmt(parseFloat(o.total_price) || 0)}</span></div>
        <div class="detail-row"><span class="label">Bezahlung</span><span class="value">${financialBadge(o.financial_status)}</span></div>
        <div class="detail-row"><span class="label">Status</span><span class="value">${fulfillmentBadge(o.fulfillment_status)}</span></div>
        <div class="detail-row"><span class="label">Shopify</span><span class="value"><a href="${o.shopify_url}" target="_blank" style="color:var(--accent)">Im Admin öffnen →</a></span></div>
    </div>`;

    // Customer info
    html += `<div class="detail-section">
        <h4>Kunde</h4>
        <div class="detail-row"><span class="label">Name</span><span class="value">${o.customer.name || '–'}</span></div>
        ${o.customer.email ? `<div class="detail-row"><span class="label">E-Mail</span><span class="value"><a href="mailto:${o.customer.email}" style="color:var(--accent)">${o.customer.email}</a></span></div>` : ''}
        ${o.customer.phone ? `<div class="detail-row"><span class="label">Telefon</span><span class="value">${o.customer.phone}</span></div>` : ''}
    </div>`;

    // Line item
    if (o.line_item) {
        html += `<div class="detail-section">
            <h4>Artikel</h4>
            <div class="detail-row"><span class="label">Produkt</span><span class="value">${o.line_item.title}</span></div>
            ${o.line_item.variant ? `<div class="detail-row"><span class="label">Variante</span><span class="value">${o.line_item.variant}</span></div>` : ''}
            <div class="detail-row"><span class="label">Anzahl</span><span class="value">${o.line_item.quantity}</span></div>
            <div class="detail-row"><span class="label">Einzelpreis</span><span class="value">${fmt(parseFloat(o.line_item.unit_price) || 0)}</span></div>
        </div>`;
    }

    // Shipping address
    if (o.shipping_address) {
        const sa = o.shipping_address;
        html += `<div class="detail-section">
            <h4>Lieferadresse</h4>
            <div class="detail-row"><span class="label">Name</span><span class="value">${sa.name || '–'}</span></div>
            <div class="detail-row"><span class="label">Adresse</span><span class="value">${[sa.address1, sa.address2, sa.city, sa.zip, sa.country].filter(Boolean).join(', ') || '–'}</span></div>
        </div>`;
    }

    // Note section (editable)
    html += `<div class="detail-section">
        <h4>Kommentar</h4>
        <textarea class="note-textarea" id="order-detail-note" placeholder="Kommentar hinzufügen…">${o.note || ''}</textarea>
        <div class="detail-actions">
            <button class="btn-sm primary" id="save-order-note-btn" onclick="saveOrderNoteFromModal('${o.shopify_order_id}')">Speichern</button>
            <span class="status-msg" id="order-note-status"></span>
        </div>
    </div>`;

    // Chronik / Events timeline
    html += '<hr class="detail-divider"><div class="detail-section"><h4>Chronik</h4>';
    if (o.events && o.events.length) {
        html += '<ul class="timeline">';
        for (const ev of o.events) {
            const date = ev.created_at
                ? new Date(ev.created_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
                : '';
            html += `<li>
                <div class="tl-time">${date}</div>
                <div class="tl-msg">${ev.message || ''}</div>
            </li>`;
        }
        html += '</ul>';
    } else {
        html += '<p style="color:var(--text-secondary);font-size:0.9rem">Keine Einträge.</p>';
    }
    html += '</div>';

    return html;
}

async function saveOrderNoteFromModal(orderId) {
    const noteEl = document.getElementById('order-detail-note');
    const statusEl = document.getElementById('order-note-status');
    const btn = document.getElementById('save-order-note-btn');

    btn.disabled = true;
    statusEl.textContent = '';
    statusEl.className = 'status-msg';

    try {
        const res = await fetch(`/api/shopify/physical-product/orders/${orderId}/note`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note: noteEl.value }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail);
        }
        statusEl.textContent = 'Gespeichert ✓';
        statusEl.className = 'status-msg ok';
        // Refresh table silently
        loadPhysicalOrders();
    } catch (e) {
        statusEl.textContent = e.message;
        statusEl.className = 'status-msg err';
    } finally {
        btn.disabled = false;
    }
}

function closeOrderModal() {
    document.getElementById('order-modal').classList.remove('open');
}

function closeTxModal() {
    document.getElementById('tx-modal').classList.remove('open');
}

function applySearch(inputId, ...rowsSelectors) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const needle = input.value.trim().toLowerCase();
    rowsSelectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(row => {
            row.style.display = !needle || row.textContent.toLowerCase().includes(needle) ? '' : 'none';
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const filterSelect = document.getElementById('status-filter');
    const refreshBtn = document.getElementById('refresh-btn');
    const txClose = document.getElementById('tx-close');
    const txOverlay = document.getElementById('tx-modal');
    const refreshOrdersBtn = document.getElementById('refresh-orders-btn');
    const orderClose = document.getElementById('order-close');
    const orderOverlay = document.getElementById('order-modal');
    const shopifySearch = document.getElementById('shopify-search');

    if (!filterSelect) return; // page not configured

    const refresh = () => {
        loadSummary();
        loadCards(filterSelect.value);
        loadPhysicalOrders();
    };

    filterSelect.addEventListener('change', () => loadCards(filterSelect.value));
    const exhaustedToggle = document.getElementById('show-exhausted');
    if (exhaustedToggle) exhaustedToggle.addEventListener('change', () => loadCards(filterSelect.value));
    refreshBtn.addEventListener('click', refresh);
    if (shopifySearch) shopifySearch.addEventListener('input', () => applySearch('shopify-search', '#cards-tbody tr', '#physical-orders-area tbody tr'));
    if (refreshOrdersBtn) refreshOrdersBtn.addEventListener('click', loadPhysicalOrders);
    txClose.addEventListener('click', closeTxModal);
    txOverlay.addEventListener('click', (e) => { if (e.target === txOverlay) closeTxModal(); });
    if (orderClose) orderClose.addEventListener('click', closeOrderModal);
    if (orderOverlay) orderOverlay.addEventListener('click', (e) => { if (e.target === orderOverlay) closeOrderModal(); });

    refresh();
});

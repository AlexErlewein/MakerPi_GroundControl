// Device Detail Page JavaScript

const API_BASE = '';

// DEVICE_ID is defined in the HTML template script tag

const REFRESH_INTERVAL = 10000; // 10 seconds

let refreshTimer = null;
let allMessages = [];
let allTopics = [];

function getElement(id) {
    const el = document.getElementById(id);
    if (!el) console.warn(`Element not found: ${id}`);
    return el;
}

function safeSetText(id, text) {
    const el = getElement(id);
    if (el) el.textContent = text;
}

function safeSetHTML(id, html) {
    const el = getElement(id);
    if (el) el.innerHTML = html;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('[DeviceDetail] Page loaded, DEVICE_ID:', DEVICE_ID);
    loadAllData();
    loadDevicePricing();
    setupEventListeners();
    startAutoRefresh();
});

// Event Listeners
function setupEventListeners() {
    const topicFilter = getElement('topic-filter');
    const exportBtn = getElement('export-btn');

    if (topicFilter) topicFilter.addEventListener('change', filterMessages);
    if (exportBtn) exportBtn.addEventListener('click', exportMessages);

    const topicsGrid = getElement('topics-grid');
    if (topicsGrid) {
        topicsGrid.addEventListener('click', (e) => {
            const topicCard = e.target.closest('.topic-card');
            if (topicCard && topicFilter) {
                const topic = topicCard.dataset.topic;
                topicFilter.value = topic;
                filterMessages();

                document.querySelectorAll('.topic-card').forEach(card => {
                    card.classList.toggle('active', card.dataset.topic === topic);
                });
            }
        });
    }
}

// Load all data
async function loadAllData() {
    console.log('[DeviceDetail] loadAllData() called, DEVICE_ID:', DEVICE_ID);
    try {
        const url = `${API_BASE}/api/devices/${encodeURIComponent(DEVICE_ID)}`;
        console.log('[DeviceDetail] Fetching:', url);
        const response = await fetch(url);
        console.log('[DeviceDetail] Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[DeviceDetail] API error:', response.status, errorText);
            throw new Error(`API error ${response.status}: ${errorText}`);
        }
        const data = await response.json();
        console.log('[DeviceDetail] Data received:', data);

        renderDeviceInfo(data.device);
        renderTopics(data.topic_counts);
        allMessages = data.recent_messages || [];
        allTopics = (data.topic_counts || []).map(t => t.topic.replace(`${DEVICE_ID}/`, ''));
        console.log('[DeviceDetail] Topics:', allTopics, 'Messages:', allMessages.length);
        populateTopicFilter();
        filterMessages();
    } catch (error) {
        console.error('[DeviceDetail] Failed to load device data:', error);
        safeSetText('device-status', 'Error');
        safeSetText('device-id', DEVICE_ID);
        safeSetText('device-name', 'Error');
        safeSetText('device-last-seen', '-');
        safeSetHTML('topics-grid', `<p class="error-text">Failed to load: ${escapeHtml(error.message)}</p>`);
        safeSetHTML('messages-container', `<div class="empty-state"><p class="error-text">Error: ${escapeHtml(error.message)}</p></div>`);
    }
}

// Render device info
function renderDeviceInfo(device) {
    safeSetText('device-id', device.device_id);
    safeSetText('device-name', device.name || 'Unnamed');
    safeSetText('device-last-seen', formatDateTime(device.last_seen));

    const statusBadge = getElement('device-status');
    if (statusBadge) {
        const effectiveStatus = getEffectiveStatus(device.last_seen);
        statusBadge.textContent = effectiveStatus;
        statusBadge.className = `status-badge ${effectiveStatus}`;
    }

    const nfcStatus = getElement('device-nfc-status');
    const nfcErrorContainer = getElement('nfc-error-container');
    const nfcError = getElement('device-nfc-error');

    if (nfcStatus) {
        if (device.nfc_ok === 1) {
            nfcStatus.innerHTML = '<span class="nfc-badge nfc-ok">✓ Working</span>';
            if (nfcErrorContainer) nfcErrorContainer.style.display = 'none';
        } else if (device.nfc_ok === 0) {
            nfcStatus.innerHTML = '<span class="nfc-badge nfc-error">✗ Error</span>';
            if (nfcErrorContainer) nfcErrorContainer.style.display = 'flex';
            if (nfcError) nfcError.textContent = device.nfc_error || 'Unknown error';
        } else {
            nfcStatus.innerHTML = '<span class="nfc-badge nfc-unknown">? Unknown</span>';
            if (nfcErrorContainer) nfcErrorContainer.style.display = 'none';
        }
    }
}

// Render topics grid
function renderTopics(topicCounts) {
    const grid = getElement('topics-grid');
    if (!grid) return;

    if (!topicCounts || topicCounts.length === 0) {
        grid.innerHTML = '<p>No topics found for this device</p>';
        return;
    }

    grid.innerHTML = topicCounts.map(t => {
        const shortTopic = t.topic.replace(`${DEVICE_ID}/`, '');
        return `
            <div class="topic-card" data-topic="${escapeHtml(shortTopic)}">
                <div class="topic-name">${escapeHtml(shortTopic)}</div>
                <div class="topic-count"><strong>${t.count}</strong> messages</div>
            </div>
        `;
    }).join('');
}

// Populate topic filter dropdown
function populateTopicFilter() {
    const tf = getElement('topic-filter');
    if (!tf) return;
    
    tf.innerHTML = '<option value="">All Topics</option>';

    allTopics.forEach(topic => {
        const option = document.createElement('option');
        option.value = topic;
        option.textContent = topic;
        tf.appendChild(option);
    });
}

// Filter messages
function filterMessages() {
    const tf = getElement('topic-filter');
    const topic = tf ? tf.value : '';
    let filtered = allMessages;

    if (topic) {
        filtered = filtered.filter(m => m.topic.includes(topic));
    }

    renderMessages(filtered);
}

// Render messages
function renderMessages(messages) {
    const container = getElement('messages-container');
    if (!container) return;

    if (!messages || messages.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No messages to display</p></div>';
        return;
    }

    container.innerHTML = messages.map(msg => {
        const shortTopic = msg.topic.replace(`${DEVICE_ID}/`, '');
        return `
            <div class="message">
                <div class="message-header">
                    <span class="message-topic">${escapeHtml(shortTopic)}</span>
                    <span class="message-time">${formatDateTime(msg.timestamp)}</span>
                </div>
                <div class="message-payload">${escapeHtml(msg.payload)}</div>
                <div class="message-meta">
                    <span class="qos-badge">QoS: ${msg.qos}</span>
                    ${msg.retained ? '<span class="retained">📌 Retained</span>' : ''}
                </div>
            </div>
        `;
    }).join('');
}

// Export messages as CSV
function exportMessages() {
    try {
        const tf = getElement('topic-filter');
        const topic = tf ? tf.value : '';
        let url = `${API_BASE}/api/export/messages?limit=1000&topic=${encodeURIComponent(DEVICE_ID)}`;
        if (topic) {
            url += `/${encodeURIComponent(topic)}`;
        }
        window.open(url, '_blank');
    } catch (error) {
        console.error('Failed to export messages:', error);
    }
}

// Auto-refresh
function startAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    refreshTimer = setInterval(loadAllData, REFRESH_INTERVAL);
    // Also poll device sessions
    loadDeviceSessions();
    setInterval(loadDeviceSessions, REFRESH_INTERVAL);
}

// ── Device Pricing Configuration ────────────────────────────────────────────

let eligibleVarianten = [];
let currentPricing = null;

async function loadDevicePricing() {
    try {
        const res = await fetch(`/api/devices/${encodeURIComponent(DEVICE_ID)}/pricing`);
        if (!res.ok) return;
        const data = await res.json();
        eligibleVarianten = data.eligible_varianten || [];
        currentPricing = data.pricing;
        renderPricingConfig();
    } catch (e) {
        console.error('[DeviceDetail] Failed to load pricing:', e);
    }
}

function renderPricingConfig() {
    const container = getElement('pricing-config-container');
    if (!container) return;

    if (!eligibleVarianten.length) {
        container.innerHTML = '<p style="color:var(--text-secondary)">Keine Katalog-Varianten mit Minuten-/Stundenpreis gefunden. Erstelle zuerst eine Variante mit pricing_model "per_minute" oder "per_hour".</p>';
        return;
    }

    const p = currentPricing;
    const isActive = p ? p.is_active : false;
    const reqPerm = p ? p.requires_permission : false;
    const selectedVarId = p ? p.variante_id : '';

    const options = eligibleVarianten.map(v => {
        const suffix = v.pricing_model === 'per_hour' ? '/h' : '/min';
        const sel = v.id === selectedVarId ? 'selected' : '';
        return `<option value="${v.id}" ${sel}>${escapeHtml(v.name)} – ${v.price.toFixed(2)} €${suffix}</option>`;
    }).join('');

    let priceDisplay = '';
    if (p) {
        const variante = eligibleVarianten.find(v => v.id === p.variante_id);
        if (variante) {
            const suffix = variante.pricing_model === 'per_hour' ? '/h' : '/min';
            priceDisplay = `<div style="margin-top:8px;font-size:1.1em;color:var(--success);font-weight:600">Aktuell: ${variante.price.toFixed(2)} €${suffix}</div>`;
        }
    }

    container.innerHTML = `
        <form id="pricing-form" style="display:flex;flex-direction:column;gap:12px">
            <div>
                <label style="font-weight:600;display:block;margin-bottom:4px">Abrechnung-Variante</label>
                <select id="pricing-variante" style="width:100%;max-width:500px;padding:8px">
                    <option value="">-- Variante wählen --</option>
                    ${options}
                </select>
            </div>
            <div style="display:flex;gap:24px;flex-wrap:wrap">
                <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
                    <input type="checkbox" id="pricing-requires-permission" ${reqPerm ? 'checked' : ''} />
                    Berechtigung erforderlich
                </label>
                <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
                    <input type="checkbox" id="pricing-is-active" ${isActive ? 'checked' : ''} />
                    Zeitabrechnung aktiv
                </label>
            </div>
            ${priceDisplay}
            <div style="display:flex;gap:8px">
                <button type="submit" class="btn btn-success" style="padding:8px 20px">Speichern</button>
                ${p ? '<button type="button" id="pricing-delete-btn" class="btn btn-danger" style="padding:8px 20px">Entfernen</button>' : ''}
            </div>
        </form>
    `;

    const form = getElement('pricing-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const varId = parseInt(getElement('pricing-variante').value);
            if (!varId) { alert('Bitte eine Variante wählen.'); return; }
            const res = await fetch(`/api/devices/${encodeURIComponent(DEVICE_ID)}/pricing`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    variante_id: varId,
                    requires_permission: getElement('pricing-requires-permission').checked,
                    is_active: getElement('pricing-is-active').checked,
                }),
            });
            if (res.ok) { loadDevicePricing(); }
            else { const err = await res.json(); alert('Fehler: ' + (err.detail || 'Speichern fehlgeschlagen')); }
        });
    }

    const delBtn = getElement('pricing-delete-btn');
    if (delBtn) {
        delBtn.addEventListener('click', async () => {
            if (!confirm('Zeitabrechnung für dieses Gerät entfernen?')) return;
            const res = await fetch(`/api/devices/${encodeURIComponent(DEVICE_ID)}/pricing`, { method: 'DELETE' });
            if (res.ok) loadDevicePricing();
            else alert('Fehler beim Löschen');
        });
    }
}

// ── Device Sessions (active + history) ──────────────────────────────────────

async function loadDeviceSessions() {
    try {
        const res = await fetch(`/api/devices/${encodeURIComponent(DEVICE_ID)}/sessions`);
        if (!res.ok) return;
        const data = await res.json();
        renderActiveSessions(data.active || []);
        renderSessionHistory(data.recent || []);
    } catch (e) {
        console.error('[DeviceDetail] Failed to load sessions:', e);
    }
}

function formatDuration(seconds) {
    if (!seconds || seconds < 0) return '0s';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

function renderActiveSessions(sessions) {
    const container = getElement('active-sessions-container');
    if (!container) return;

    if (!sessions.length) {
        container.innerHTML = '<p style="color:var(--text-secondary)">Keine aktiven Sitzungen.</p>';
        return;
    }

    container.innerHTML = `
        <table style="width:100%;border-collapse:collapse">
            <thead>
                <tr style="text-align:left;border-bottom:2px solid var(--border-color)">
                    <th style="padding:8px">UID</th>
                    <th style="padding:8px">Benutzer</th>
                    <th style="padding:8px">Start</th>
                    <th style="padding:8px">Dauer</th>
                    <th style="padding:8px">Aktion</th>
                </tr>
            </thead>
            <tbody>
                ${sessions.map(s => {
                    const startMs = new Date(s.start_time).getTime();
                    return `
                    <tr style="border-bottom:1px solid var(--border-color)" data-start-ms="${startMs}">
                        <td style="padding:8px;font-family:monospace">${escapeHtml(s.uid)}</td>
                        <td style="padding:8px">${escapeHtml(s.owner_name || s.guest_id || '—')}</td>
                        <td style="padding:8px">${formatDateTime(s.start_time)}</td>
                        <td class="duration-cell" style="padding:8px;font-family:monospace" data-start-ms="${startMs}">—</td>
                        <td style="padding:8px">
                            <button class="btn btn-danger end-session-btn" data-session-id="${s.id}" style="padding:4px 12px;font-size:0.85rem">Beenden</button>
                        </td>
                    </tr>`;
                }).join('')}
            </tbody>
        </table>
    `;

    container.querySelectorAll('.end-session-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const sid = btn.dataset.sessionId;
            if (!confirm('Sitzung beenden und abrechnen?')) return;
            const res = await fetch(`/api/devices/${encodeURIComponent(DEVICE_ID)}/sessions/${sid}/stop`, { method: 'POST' });
            if (res.ok) loadDeviceSessions();
            else { const err = await res.json(); alert('Fehler: ' + (err.detail || 'Beenden fehlgeschlagen')); }
        });
    });
}

function renderSessionHistory(sessions) {
    const container = getElement('session-history-container');
    if (!container) return;

    if (!sessions.length) {
        container.innerHTML = '<p style="color:var(--text-secondary)">Keine vergangenen Sitzungen.</p>';
        return;
    }

    container.innerHTML = `
        <table style="width:100%;border-collapse:collapse;font-size:0.9rem">
            <thead>
                <tr style="text-align:left;border-bottom:2px solid var(--border-color)">
                    <th style="padding:6px">UID</th>
                    <th style="padding:6px">Benutzer</th>
                    <th style="padding:6px">Start</th>
                    <th style="padding:6px">Ende</th>
                    <th style="padding:6px">Dauer</th>
                    <th style="padding:6px">Preis</th>
                    <th style="padding:6px">Beendet durch</th>
                </tr>
            </thead>
            <tbody>
                ${sessions.map(s => `
                    <tr style="border-bottom:1px solid var(--border-color)">
                        <td style="padding:6px;font-family:monospace">${escapeHtml(s.uid)}</td>
                        <td style="padding:6px">${escapeHtml(s.owner_name || s.guest_id || '—')}</td>
                        <td style="padding:6px">${formatDateTime(s.start_time)}</td>
                        <td style="padding:6px">${formatDateTime(s.end_time)}</td>
                        <td style="padding:6px;font-family:monospace">${formatDuration(s.duration_seconds)}</td>
                        <td style="padding:6px;font-family:monospace;color:var(--success)">${s.calculated_price != null ? s.calculated_price.toFixed(2) + ' €' : '—'}</td>
                        <td style="padding:6px">${escapeHtml(s.ended_by || '—')}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Live duration counter — updates every second
setInterval(() => {
    document.querySelectorAll('.duration-cell').forEach(cell => {
        const startMs = parseFloat(cell.dataset.startMs);
        if (isNaN(startMs)) return;
        const elapsed = Math.floor((Date.now() - startMs) / 1000);
        cell.textContent = formatDuration(elapsed);
    });
}, 1000);

// Get effective status based on last_seen timestamp
function getEffectiveStatus(lastSeen) {
    if (!lastSeen) return 'unknown';

    const lastSeenDate = new Date(lastSeen);
    if (isNaN(lastSeenDate.getTime())) return 'unknown';

    const now = new Date();
    const diff = now - lastSeenDate;

    // Offline if no heartbeat for 2 minutes
    if (diff > 120000) {
        return 'offline';
    }

    return 'online';
}

// Utility functions
function formatDateTime(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return 'Invalid date';
    return date.toLocaleString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Devices Page JavaScript

const API_BASE = '';
const REFRESH_INTERVAL = 500; // 0.5 seconds

let refreshTimer = null;
let allDevices = [];
// DOM Elements
const statusFilter = document.getElementById('status-filter');
const nfcFilter = document.getElementById('nfc-filter');
const deviceSearch = document.getElementById('device-search');
const refreshBtn = document.getElementById('refresh-btn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadAllData();
    setupEventListeners();
    startAutoRefresh();
    loadNfcReaderWriterSettings();
    loadPaymentReaderSettings();
});

// Event Listeners
function setupEventListeners() {
    if (refreshBtn) refreshBtn.addEventListener('click', loadAllData);
    statusFilter.addEventListener('change', filterDevices);
    nfcFilter.addEventListener('change', filterDevices);
    deviceSearch.addEventListener('input', debounce(filterDevices, 300));

    const topicFilterEl = document.getElementById('topic-filter');
    if (topicFilterEl) {
        topicFilterEl.addEventListener('input', debounce(() => {
            loadMessages(topicFilterEl.value);
        }, 300));
    }

    // Export buttons
    document.querySelectorAll('.export-btn').forEach(btn => {
        btn.addEventListener('click', () => exportData(btn.dataset.type));
    });
}

// Load all data
async function loadAllData() {
    await Promise.all([
        loadStats(),
        loadDevices(),
        loadMessages((document.getElementById('topic-filter') || {}).value || '')
    ]);
}

// Load stats
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/database/stats`);
        if (!response.ok) return;
        const stats = await response.json();

        const el = (id) => document.getElementById(id);
        if (el('device-count')) el('device-count').textContent = stats.devices.total;
        if (el('online-count')) el('online-count').textContent = stats.devices.online;
        if (el('offline-count')) el('offline-count').textContent = stats.devices.offline;
        if (el('message-count')) el('message-count').textContent = stats.messages.total;
        if (el('topic-count')) el('topic-count').textContent = stats.messages.topics;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Load native devices
async function loadDevices() {
    try {
        const response = await fetch(`${API_BASE}/api/devices`);
        if (!response.ok) throw new Error(`API error ${response.status}`);
        allDevices = await response.json();
        filterDevices();
    } catch (error) {
        console.error('Failed to load devices:', error);
        const tbody = document.getElementById('devices-body');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" class="error-text">Error loading devices</td></tr>`;
        }
    }
}

// Load messages
async function loadMessages(topicFilter) {
    try {
        let url = `${API_BASE}/api/messages?limit=50`;
        if (topicFilter) {
            url += `&topic=${encodeURIComponent(topicFilter)}`;
        }
        const response = await fetch(url);
        if (!response.ok) return;
        const messages = await response.json();

        const container = document.getElementById('messages-container');
        if (!container) return;

        if (messages.length === 0) {
            container.innerHTML = '<p>No messages found</p>';
            return;
        }

        container.innerHTML = messages.map(msg => {
            let badge = '';
            if (msg.pairing_status) {
                const name = msg.pairing_name ? escapeHtml(msg.pairing_name) : '';
                if (msg.pairing_status === 'member') {
                    badge = `<span class="pairing-badge pairing-member" title="${name}">✓ Member</span>`;
                } else if (msg.pairing_status === 'guest') {
                    const lzId = msg.pairing_laufzettel_id ? ' #' + msg.pairing_laufzettel_id : '';
                    badge = `<span class="pairing-badge pairing-guest" title="${name}">👥 Guest${lzId}</span>`;
                } else {
                    badge = `<span class="pairing-badge pairing-unpaired">⚠ Unpaired</span>`;
                }
            }
            return `
            <div class="message">
                <span class="message-time">${formatTime(msg.timestamp)}</span>
                <span class="message-topic">${escapeHtml(msg.topic)}</span>
                ${badge}
                <div class="message-payload">${escapeHtml(msg.payload)}</div>
            </div>
        `}).join('');
    } catch (error) {
        console.error('Failed to load messages:', error);
    }
}

// Filter native devices
function filterDevices() {
    const status = statusFilter ? statusFilter.value : '';
    const nfc = nfcFilter ? nfcFilter.value : '';
    const search = deviceSearch ? deviceSearch.value.toLowerCase() : '';

    let filtered = allDevices;

    if (status) {
        filtered = filtered.filter(d => getEffectiveStatus(d.last_seen) === status);
    }
    if (nfc === 'ok') {
        filtered = filtered.filter(d => d.nfc_ok === 1);
    } else if (nfc === 'error') {
        filtered = filtered.filter(d => d.nfc_ok === 0);
    } else if (nfc === 'unknown') {
        filtered = filtered.filter(d => d.nfc_ok === null || d.nfc_ok === undefined);
    }
    if (search) {
        filtered = filtered.filter(d =>
            d.device_id.toLowerCase().includes(search) ||
            (d.name && d.name.toLowerCase().includes(search))
        );
    }

    renderDevices(filtered);
}

// Render native devices table
function renderDevices(devices) {
    const tbody = document.getElementById('devices-body');
    if (!tbody) return;

    if (devices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No devices match the current filters</td></tr>';
        return;
    }

    tbody.innerHTML = devices.map(device => {
        const effectiveStatus = getEffectiveStatus(device.last_seen);
        return `
        <tr>
            <td><a href="/devices/${encodeURIComponent(device.device_id)}" class="device-link">
                <code>${escapeHtml(device.device_id)}</code>
            </a></td>
            <td>${escapeHtml(device.name || 'Unnamed')}</td>
            <td><span class="status-badge ${effectiveStatus}">${effectiveStatus}</span></td>
            <td>
                ${device.nfc_ok === 1 ? '<span class="nfc-badge nfc-ok">✓ OK</span>'
                  : device.nfc_ok === 0 ? '<span class="nfc-badge nfc-error">✗ Error</span>'
                  : '<span class="nfc-badge nfc-unknown">? Unknown</span>'}
            </td>
            <td>${formatTime(device.last_seen)}</td>
            <td class="actions-cell">
                <a href="/devices/${encodeURIComponent(device.device_id)}"
                   class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;">View</a>
                <button onclick="deleteDevice('${escapeHtml(device.device_id)}')"
                        class="btn btn-danger" style="padding: 4px 10px; font-size: 0.8rem; margin-left: 4px;">Delete</button>
            </td>
        </tr>
    `}).join('');
}

// Delete device
async function deleteDevice(deviceId) {
    if (!confirm(`Delete device "${deviceId}"?\nIt will reappear only when it actively sends a live message.`)) return;
    try {
        const response = await fetch(`${API_BASE}/api/devices/${encodeURIComponent(deviceId)}`, { method: 'DELETE' });
        if (!response.ok) {
            const error = await response.json();
            alert(`Failed: ${error.detail || 'Unknown error'}`);
            return;
        }
        await loadAllData();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Export data
function exportData(type) {
    window.open(`${API_BASE}/api/export/${type}`, '_blank');
}

// ── NFC Reader/Writer Settings (combined) ───────────────────────────────────

function setNfcReaderWriterStatus(msg, type) {
    const el = document.getElementById('nfc-reader-writer-status');
    if (!el) return;
    if (!msg) { el.style.display = 'none'; return; }
    el.style.display = 'block';
    el.textContent = msg;
    el.style.background = type === 'ok' ? '#1a3a1a' : type === 'error' ? '#3a1a1a' : '#1a2a3a';
    el.style.color = type === 'ok' ? '#3fb950' : type === 'error' ? '#f85149' : '#79c0ff';
    el.style.border = `1px solid ${type === 'ok' ? '#238636' : type === 'error' ? '#da3633' : '#1f6feb'}`;
}

async function loadNfcReaderWriterSettings() {
    try {
        // Fetch both settings in parallel
        const [enrollmentRes, writerRes] = await Promise.all([
            fetch('/api/settings/enrollment-reader'),
            fetch('/api/settings/card-writer')
        ]);
        if (!enrollmentRes.ok || !writerRes.ok) return;

        const enrollmentData = await enrollmentRes.json();
        const writerData = await writerRes.json();

        const select = document.getElementById('nfc-reader-writer-select');
        if (!select) return;

        // Use enrollment reader as the primary value (they should be the same)
        const current = enrollmentData.enrollment_reader_id || '';
        select.innerHTML = '<option value="">— Kein Gerät auswählen —</option>';
        (enrollmentData.devices || []).forEach(dev => {
            const id = typeof dev === 'object' ? dev.id : dev;
            const label = typeof dev === 'object' && dev.name !== dev.id ? `${dev.name} (${dev.id})` : id;
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = label;
            if (id === current) opt.selected = true;
            select.appendChild(opt);
        });

        const saveBtn = document.getElementById('save-nfc-reader-writer');
        if (saveBtn && !saveBtn._listenerAttached) {
            saveBtn._listenerAttached = true;
            saveBtn.addEventListener('click', saveNfcReaderWriter);
        }
    } catch (e) {
        console.error('Failed to load NFC reader/writer settings:', e);
    }
}

async function saveNfcReaderWriter() {
    const select = document.getElementById('nfc-reader-writer-select');
    const saveBtn = document.getElementById('save-nfc-reader-writer');
    if (!select) return;
    const newId = select.value;
    saveBtn.disabled = true;
    try {
        // Save both settings to the same device
        const [enrollmentRes, writerRes] = await Promise.all([
            fetch('/api/settings/enrollment-reader', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enrollment_reader_id: newId }),
            }),
            fetch('/api/settings/card-writer', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ card_writer_id: newId }),
            })
        ]);

        if (enrollmentRes.ok && writerRes.ok) {
            setNfcReaderWriterStatus(newId ? `✓ Gerät: ${newId}` : '✓ Kein Gerät konfiguriert', 'ok');
        } else {
            const err = await enrollmentRes.json().catch(() => ({ detail: 'Speichern fehlgeschlagen' }));
            setNfcReaderWriterStatus('Fehler: ' + (err.detail || 'Speichern fehlgeschlagen'), 'error');
        }
    } catch (e) {
        setNfcReaderWriterStatus('Verbindungsfehler', 'error');
    } finally {
        saveBtn.disabled = false;
    }
}

// ── Payment Reader Settings ───────────────────────────────────────────────────

function setPaymentReaderStatus(msg, type) {
    const el = document.getElementById('payment-reader-status');
    if (!el) return;
    if (!msg) { el.style.display = 'none'; return; }
    el.style.display = 'block';
    el.textContent = msg;
    el.style.background = type === 'ok' ? '#1a3a1a' : type === 'error' ? '#3a1a1a' : '#1a2a3a';
    el.style.color = type === 'ok' ? '#3fb950' : type === 'error' ? '#f85149' : '#79c0ff';
    el.style.border = `1px solid ${type === 'ok' ? '#238636' : type === 'error' ? '#da3633' : '#1f6feb'}`;
}

async function loadPaymentReaderSettings() {
    try {
        const res = await fetch('/api/settings/payment-reader');
        if (!res.ok) return;
        const data = await res.json();
        const select = document.getElementById('payment-reader-select');
        if (!select) return;

        const current = data.payment_reader_id || '';
        select.innerHTML = '<option value="">— Keinen Reader auswählen —</option>';
        (data.devices || []).forEach(dev => {
            const id = typeof dev === 'object' ? dev.id : dev;
            const label = typeof dev === 'object' && dev.name !== dev.id ? `${dev.name} (${dev.id})` : id;
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = label;
            if (id === current) opt.selected = true;
            select.appendChild(opt);
        });

        const saveBtn = document.getElementById('save-payment-reader');
        if (saveBtn && !saveBtn._listenerAttached) {
            saveBtn._listenerAttached = true;
            saveBtn.addEventListener('click', savePaymentReader);
        }
    } catch (e) {
        console.error('Failed to load payment reader settings:', e);
    }
}

async function savePaymentReader() {
    const select = document.getElementById('payment-reader-select');
    const saveBtn = document.getElementById('save-payment-reader');
    if (!select) return;
    const newId = select.value;
    saveBtn.disabled = true;
    try {
        const res = await fetch('/api/settings/payment-reader', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ payment_reader_id: newId }),
        });
        if (res.ok) {
            setPaymentReaderStatus(newId ? `✓ Reader: ${newId}` : '✓ Kein Reader konfiguriert', 'ok');
        } else {
            const err = await res.json();
            setPaymentReaderStatus('Fehler: ' + (err.detail || 'Speichern fehlgeschlagen'), 'error');
        }
    } catch (e) {
        setPaymentReaderStatus('Verbindungsfehler', 'error');
    } finally {
        saveBtn.disabled = false;
    }
}

// ── Auto-refresh ─────────────────────────────────────────────────────────────

function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(loadAllData, REFRESH_INTERVAL);
}

// ── Utilities ────────────────────────────────────────────────────────────────

function getEffectiveStatus(lastSeen) {
    if (!lastSeen) return 'unknown';
    const lastSeenDate = new Date(lastSeen);
    if (isNaN(lastSeenDate.getTime())) return 'unknown';
    const diff = Date.now() - lastSeenDate.getTime();
    return diff > 120000 ? 'offline' : 'online';
}

function formatTime(timestamp) {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return '—';
    const diff = Date.now() - date.getTime();
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleString();
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

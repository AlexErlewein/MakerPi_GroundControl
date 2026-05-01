// MakerPi GroundControl - Frontend Application

const API_BASE = '';
const REFRESH_INTERVAL = 5000; // 5 seconds

let refreshTimer = null;

// DOM Elements
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const deviceCount = document.getElementById('device-count');
const zigbeeDeviceCount = document.getElementById('zigbee-device-count');
const messageCount = document.getElementById('message-count');
const topicCount = document.getElementById('topic-count');
const devicesBody = document.getElementById('devices-body');
const zigbeeDevicesBody = document.getElementById('zigbee-devices-body');
const messagesContainer = document.getElementById('messages-container');
const topicFilter = document.getElementById('topic-filter');
const refreshBtn = document.getElementById('refresh-btn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadAllData();
    setupEventListeners();
    startAutoRefresh();
    loadEnrollmentReaderSettings();
});

// Event Listeners
function setupEventListeners() {
    refreshBtn.addEventListener('click', loadAllData);

    topicFilter.addEventListener('input', debounce(() => {
        loadMessages(topicFilter.value);
    }, 300));
}

// Load all data
async function loadAllData() {
    await Promise.all([
        loadStatus(),
        loadDevices(),
        loadZigbeeDevices(),
        loadMessages(topicFilter.value),
        loadTopics()
    ]);
}

// Load system status
async function loadStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();

        if (data.mqtt_connected) {
            statusDot.className = 'status-dot online';
            statusText.textContent = 'MQTT Connected';
        } else {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'MQTT Disconnected';
        }
    } catch (error) {
        console.error('Failed to load status:', error);
        statusDot.className = 'status-dot offline';
        statusText.textContent = 'Connection Error';
    }
}

// Load devices
async function loadDevices() {
    try {
        const response = await fetch(`${API_BASE}/api/devices`);
        const devices = await response.json();

        deviceCount.textContent = devices.length;

        if (devices.length === 0) {
            devicesBody.innerHTML = '<tr><td colspan="4">No devices found</td></tr>';
            return;
        }

        devicesBody.innerHTML = devices.map(device => {
            const effectiveStatus = getEffectiveStatus(device.last_seen);
            return `
            <tr>
                <td><code>${escapeHtml(device.device_id)}</code></td>
                <td>${escapeHtml(device.name)}</td>
                <td>
                    <span class="status-badge ${effectiveStatus}">${effectiveStatus}</span>
                    ${device.nfc_ok !== null && device.nfc_ok !== undefined ? `
                        <span class="nfc-badge ${device.nfc_ok ? 'nfc-ok' : 'nfc-error'}" title="${device.nfc_error || 'NFC OK'}">
                            NFC: ${device.nfc_ok ? '✓' : '✗'}
                        </span>
                    ` : '<span class="nfc-badge nfc-unknown">NFC: ?</span>'}
                </td>
                <td>${formatTime(device.last_seen)}</td>
            </tr>
        `}).join('');
    } catch (error) {
        console.error('Failed to load devices:', error);
        devicesBody.innerHTML = '<tr><td colspan="4">Error loading devices</td></tr>';
    }
}

// Load Zigbee devices
async function loadZigbeeDevices() {
    try {
        const response = await fetch(`${API_BASE}/api/zigbee-devices`);
        const devices = await response.json();

        zigbeeDeviceCount.textContent = devices.length;

        if (devices.length === 0) {
            zigbeeDevicesBody.innerHTML = '<tr><td colspan="7">No Zigbee devices found. Devices will appear when they send data via zigbee2mqtt.</td></tr>';
            return;
        }

        zigbeeDevicesBody.innerHTML = devices.map(device => {
            const effectiveStatus = getEffectiveStatus(device.last_seen);
            const displayName = device.friendly_name || device.ieee_address || 'Unknown';
            const batteryDisplay = device.battery !== null && device.battery !== undefined
                ? `<span class="battery-level ${device.battery < 20 ? 'low' : device.battery < 50 ? 'medium' : 'good'}">${device.battery}%</span>`
                : '<span class="battery-unknown">—</span>';
            const linkqualityDisplay = device.linkquality !== null && device.linkquality !== undefined
                ? `<span class="linkquality ${device.linkquality < 50 ? 'weak' : device.linkquality < 100 ? 'medium' : 'good'}">${device.linkquality}</span>`
                : '<span class="linkquality-unknown">—</span>';

            return `
            <tr>
                <td><strong>${escapeHtml(displayName)}</strong></td>
                <td><code class="ieee-address">${escapeHtml(device.ieee_address || '—')}</code></td>
                <td>${escapeHtml(device.model || '—')}</td>
                <td><span class="status-badge ${effectiveStatus}">${effectiveStatus}</span></td>
                <td>${batteryDisplay}</td>
                <td>${linkqualityDisplay}</td>
                <td>${formatTime(device.last_seen)}</td>
            </tr>
        `}).join('');
    } catch (error) {
        console.error('Failed to load Zigbee devices:', error);
        zigbeeDevicesBody.innerHTML = '<tr><td colspan="7">Error loading Zigbee devices</td></tr>';
    }
}

// Load messages
async function loadMessages(topicFilter = '') {
    try {
        let url = `${API_BASE}/api/messages?limit=50`;
        if (topicFilter) {
            url += `&topic=${encodeURIComponent(topicFilter)}`;
        }

        const response = await fetch(url);
        const messages = await response.json();

        messageCount.textContent = messages.length;

        if (messages.length === 0) {
            messagesContainer.innerHTML = '<p>No messages found</p>';
            return;
        }

        messagesContainer.innerHTML = messages.map(msg => `
            <div class="message">
                <span class="message-time">${formatTime(msg.timestamp)}</span>
                <span class="message-topic">${escapeHtml(msg.topic)}</span>
                <div class="message-payload">${escapeHtml(msg.payload)}</div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load messages:', error);
        messagesContainer.innerHTML = '<p>Error loading messages</p>';
    }
}

// Load topics
async function loadTopics() {
    try {
        const response = await fetch(`${API_BASE}/api/topics`);
        const topics = await response.json();
        topicCount.textContent = topics.length;
    } catch (error) {
        console.error('Failed to load topics:', error);
        topicCount.textContent = '-';
    }
}

// Auto-refresh
function startAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    refreshTimer = setInterval(loadAllData, REFRESH_INTERVAL);
}

// Get effective status based on last_seen timestamp
function getEffectiveStatus(lastSeen) {
    if (!lastSeen) return 'unknown';

    const lastSeenDate = new Date(lastSeen);
    if (isNaN(lastSeenDate.getTime())) return 'unknown';

    const now = new Date();
    const diff = now - lastSeenDate;

    // Debug logging
    console.log(`[Status] Device last seen: ${lastSeenDate.toISOString()}, Now: ${now.toISOString()}, Diff: ${Math.floor(diff/1000)}s`);

    // Offline if no heartbeat for 2 minutes
    if (diff > 120000) {
        return 'offline';
    }

    return 'online';
}

// Utility functions
function formatTime(timestamp) {
    if (!timestamp) return 'Unknown';

    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return 'Invalid';
    
    const now = new Date();
    const diff = now - date;

    // Less than a minute
    if (diff < 60000) {
        return 'Just now';
    }

    // Less than an hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}m ago`;
    }

    // Less than a day
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    }

    // More than a day
    return date.toLocaleString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ── Enrollment Reader Settings ────────────────────────────────────────────────

function setEnrollmentStatus(msg, type) {
    const el = document.getElementById('enrollment-reader-status');
    if (!msg) { el.style.display = 'none'; return; }
    el.style.display = 'block';
    el.textContent = msg;
    el.style.background = type === 'ok' ? '#1a3a1a' : type === 'error' ? '#3a1a1a' : '#1a2a3a';
    el.style.color = type === 'ok' ? '#3fb950' : type === 'error' ? '#f85149' : '#79c0ff';
    el.style.border = `1px solid ${type === 'ok' ? '#238636' : type === 'error' ? '#da3633' : '#1f6feb'}`;
}

async function loadEnrollmentReaderSettings() {
    try {
        const res = await fetch('/api/settings/enrollment-reader');
        if (!res.ok) return;
        const data = await res.json();
        const select = document.getElementById('enrollment-reader-select');
        if (!select) return;

        // Populate options from known devices
        const current = data.enrollment_reader_id || '';
        // Keep the empty option, add device options
        select.innerHTML = '<option value="">— Keinen Reader auswählen —</option>';
        (data.devices || []).forEach(id => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = id;
            if (id === current) opt.selected = true;
            select.appendChild(opt);
        });

        // Attach save button listener (once)
        const saveBtn = document.getElementById('save-enrollment-reader');
        if (saveBtn && !saveBtn._listenerAttached) {
            saveBtn._listenerAttached = true;
            saveBtn.addEventListener('click', saveEnrollmentReader);
        }
    } catch (e) {
        console.error('Failed to load enrollment reader settings:', e);
    }
}

async function saveEnrollmentReader() {
    const select = document.getElementById('enrollment-reader-select');
    const saveBtn = document.getElementById('save-enrollment-reader');
    if (!select) return;
    const newId = select.value;
    saveBtn.disabled = true;
    try {
        const res = await fetch('/api/settings/enrollment-reader', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enrollment_reader_id: newId }),
        });
        if (res.ok) {
            setEnrollmentStatus(
                newId ? `✓ Reader gesetzt: ${newId}` : '✓ Kein Reader konfiguriert',
                'ok'
            );
        } else {
            const err = await res.json();
            setEnrollmentStatus('Fehler: ' + (err.detail || 'Speichern fehlgeschlagen'), 'error');
        }
    } catch (e) {
        setEnrollmentStatus('Verbindungsfehler beim Speichern.', 'error');
    } finally {
        saveBtn.disabled = false;
    }
}

// Database Page JavaScript

const API_BASE = '';
const REFRESH_INTERVAL = 10000; // 10 seconds

let refreshTimer = null;
let allDevices = [];

// DOM Elements
const refreshBtn = document.getElementById('refresh-btn');
const statusFilter = document.getElementById('status-filter');
const nfcFilter = document.getElementById('nfc-filter');
const deviceSearch = document.getElementById('device-search');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadAllData();
    setupEventListeners();
    startAutoRefresh();
});

// Event Listeners
function setupEventListeners() {
    refreshBtn.addEventListener('click', loadAllData);

    statusFilter.addEventListener('change', filterDevices);
    nfcFilter.addEventListener('change', filterDevices);
    deviceSearch.addEventListener('input', debounce(filterDevices, 300));

    // Export buttons
    document.querySelectorAll('.export-btn').forEach(btn => {
        btn.addEventListener('click', () => exportData(btn.dataset.type));
    });
}

// Load all data
async function loadAllData() {
    await Promise.all([
        loadDatabaseStats(),
        loadDevices()
    ]);
}

// Load database statistics
async function loadDatabaseStats() {
    try {
        const response = await fetch(`${API_BASE}/api/database/stats`);
        if (!response.ok) {
            throw new Error(`API error ${response.status}`);
        }
        const stats = await response.json();

        // Database info
        document.getElementById('db-path').textContent = stats.database.file_path;
        document.getElementById('db-size').textContent = stats.database.size_human;

        // Device stats
        document.getElementById('device-count').textContent = stats.devices.total;
        document.getElementById('online-count').textContent = stats.devices.online;
        document.getElementById('offline-count').textContent = stats.devices.offline;
        document.getElementById('nfc-ok-count').textContent = stats.devices.nfc_ok;
        document.getElementById('nfc-error-count').textContent = stats.devices.nfc_error;
        document.getElementById('nfc-unknown-count').textContent = stats.devices.nfc_unknown;

        // Message stats
        document.getElementById('message-count').textContent = stats.messages.total;
        document.getElementById('topic-count').textContent = stats.messages.topics;
        document.getElementById('oldest-message').textContent = stats.messages.oldest
            ? formatDateTime(stats.messages.oldest)
            : 'No data';
        document.getElementById('newest-message').textContent = stats.messages.newest
            ? formatDateTime(stats.messages.newest)
            : 'No data';

        // Activity stats
        document.getElementById('oldest-device').textContent = stats.devices_oldest_seen
            ? formatDateTime(stats.devices_oldest_seen)
            : 'No data';
        document.getElementById('newest-device').textContent = stats.devices_newest_seen
            ? formatDateTime(stats.devices_newest_seen)
            : 'No data';

    } catch (error) {
        console.error('Failed to load database stats:', error);
    }
}

// Load devices
async function loadDevices() {
    try {
        const response = await fetch(`${API_BASE}/api/devices`);
        if (!response.ok) {
            throw new Error(`API error ${response.status}`);
        }
        allDevices = await response.json();
        filterDevices();
    } catch (error) {
        console.error('Failed to load devices:', error);
        const tbody = document.getElementById('devices-body');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" class="error-text">Error loading devices: ${escapeHtml(error.message)}</td></tr>`;
        }
    }
}

// Filter devices
function filterDevices() {
    const status = statusFilter.value;
    const nfc = nfcFilter.value;
    const search = deviceSearch.value.toLowerCase();

    let filtered = allDevices;

    if (status) {
        filtered = filtered.filter(d => d.status === status);
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

// Render devices table
function renderDevices(devices) {
    const tbody = document.getElementById('devices-body');

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
            <td>
                <span class="status-badge ${effectiveStatus}">${effectiveStatus}</span>
            </td>
            <td>
                ${device.nfc_ok === 1 ? '<span class="nfc-badge nfc-ok">✓ OK</span>'
                  : device.nfc_ok === 0 ? '<span class="nfc-badge nfc-error">✗ Error</span>'
                  : '<span class="nfc-badge nfc-unknown">? Unknown</span>'}
            </td>
            <td>${formatTime(device.last_seen)}</td>
            <td>
                <a href="/devices/${encodeURIComponent(device.device_id)}"
                   class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;">View</a>
            </td>
        </tr>
    `}).join('');
}

// Export data
async function exportData(type) {
    try {
        const url = `${API_BASE}/api/export/${type}`;
        window.open(url, '_blank');
    } catch (error) {
        console.error('Failed to export:', error);
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

    // Offline if no heartbeat for 5 minutes
    if (diff > 300000) {
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

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}m ago`;
    }
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    }
    return date.toLocaleDateString();
}

function formatDateTime(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return 'Invalid';
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

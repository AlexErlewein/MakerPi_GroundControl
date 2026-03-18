// MakerPi GroundControl - Frontend Application

const API_BASE = '';
const REFRESH_INTERVAL = 5000; // 5 seconds

let refreshTimer = null;

// DOM Elements
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const deviceCount = document.getElementById('device-count');
const messageCount = document.getElementById('message-count');
const topicCount = document.getElementById('topic-count');
const devicesBody = document.getElementById('devices-body');
const messagesContainer = document.getElementById('messages-container');
const topicFilter = document.getElementById('topic-filter');
const refreshBtn = document.getElementById('refresh-btn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadAllData();
    setupEventListeners();
    startAutoRefresh();
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

        devicesBody.innerHTML = devices.map(device => `
            <tr>
                <td><code>${escapeHtml(device.device_id)}</code></td>
                <td>${escapeHtml(device.name)}</td>
                <td>
                    <span class="status-badge ${device.status}">${device.status}</span>
                    ${device.nfc_ok !== null && device.nfc_ok !== undefined ? `
                        <span class="nfc-badge ${device.nfc_ok ? 'nfc-ok' : 'nfc-error'}" title="${device.nfc_error || 'NFC OK'}">
                            NFC: ${device.nfc_ok ? '✓' : '✗'}
                        </span>
                    ` : '<span class="nfc-badge nfc-unknown">NFC: ?</span>'}
                </td>
                <td>${formatTime(device.last_seen)}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load devices:', error);
        devicesBody.innerHTML = '<tr><td colspan="4">Error loading devices</td></tr>';
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

// Utility functions
function formatTime(timestamp) {
    if (!timestamp) return 'Unknown';

    const date = new Date(timestamp);
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

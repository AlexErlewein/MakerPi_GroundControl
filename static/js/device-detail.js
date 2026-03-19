// Device Detail Page JavaScript

const API_BASE = '';
const DEVICE_ID = typeof DEVICE_ID !== 'undefined' ? DEVICE_ID :
    window.location.pathname.split('/').pop();

const REFRESH_INTERVAL = 10000; // 10 seconds

let refreshTimer = null;
let allMessages = [];
let allTopics = [];

// DOM Elements
const refreshBtn = document.getElementById('refresh-btn');
const topicFilter = document.getElementById('topic-filter');
const exportBtn = document.getElementById('export-btn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadAllData();
    setupEventListeners();
    startAutoRefresh();
});

// Event Listeners
function setupEventListeners() {
    refreshBtn.addEventListener('click', loadAllData);
    topicFilter.addEventListener('change', filterMessages);
    exportBtn.addEventListener('click', exportMessages);

    // Topic card clicks
    document.getElementById('topics-grid').addEventListener('click', (e) => {
        const topicCard = e.target.closest('.topic-card');
        if (topicCard) {
            const topic = topicCard.dataset.topic;
            topicFilter.value = topic;
            filterMessages();

            // Update active state
            document.querySelectorAll('.topic-card').forEach(card => {
                card.classList.toggle('active', card.dataset.topic === topic);
            });
        }
    });
}

// Load all data
async function loadAllData() {
    try {
        const response = await fetch(`${API_BASE}/api/devices/${encodeURIComponent(DEVICE_ID)}`);
        const data = await response.json();

        renderDeviceInfo(data.device);
        renderTopics(data.topic_counts);
        allMessages = data.recent_messages;
        allTopics = data.topic_counts.map(t => t.topic.replace(`${DEVICE_ID}/`, ''));
        populateTopicFilter();
        filterMessages();
    } catch (error) {
        console.error('Failed to load device data:', error);
        if (error.message?.includes('404') || error.status === 404) {
            document.querySelector('main').innerHTML =
                '<div class="empty-state"><div class="empty-state-icon">🔍</div>' +
                '<p class="empty-state-text">Device not found</p></div>';
        }
    }
}

// Render device info
function renderDeviceInfo(device) {
    document.getElementById('device-id').textContent = device.device_id;
    document.getElementById('device-name').textContent = device.name || 'Unnamed';
    document.getElementById('device-last-seen').textContent = formatDateTime(device.last_seen);

    // Status badge
    const statusBadge = document.getElementById('device-status');
    statusBadge.textContent = device.status;
    statusBadge.className = `status-badge ${device.status}`;

    // NFC status
    const nfcStatus = document.getElementById('device-nfc-status');
    const nfcErrorContainer = document.getElementById('nfc-error-container');
    const nfcError = document.getElementById('device-nfc-error');

    if (device.nfc_ok === 1) {
        nfcStatus.innerHTML = '<span class="nfc-badge nfc-ok">✓ Working</span>';
        nfcErrorContainer.style.display = 'none';
    } else if (device.nfc_ok === 0) {
        nfcStatus.innerHTML = '<span class="nfc-badge nfc-error">✗ Error</span>';
        nfcErrorContainer.style.display = 'flex';
        nfcError.textContent = device.nfc_error || 'Unknown error';
    } else {
        nfcStatus.innerHTML = '<span class="nfc-badge nfc-unknown">? Unknown</span>';
        nfcErrorContainer.style.display = 'none';
    }
}

// Render topics grid
function renderTopics(topicCounts) {
    const grid = document.getElementById('topics-grid');

    if (topicCounts.length === 0) {
        grid.innerHTML = '<p>No topics found for this device</p>';
        return;
    }

    grid.innerHTML = topicCounts.map(t => {
        const shortTopic = t.topic.replace(`${DEVICE_ID}/`, '');
        return `
            <div class="topic-card" data-topic="${shortTopic}">
                <div class="topic-name">${escapeHtml(shortTopic)}</div>
                <div class="topic-count"><strong>${t.count}</strong> messages</div>
            </div>
        `;
    }).join('');
}

// Populate topic filter dropdown
function populateTopicFilter() {
    // Clear existing options except "All Topics"
    topicFilter.innerHTML = '<option value="">All Topics</option>';

    allTopics.forEach(topic => {
        const option = document.createElement('option');
        option.value = topic;
        option.textContent = topic;
        topicFilter.appendChild(option);
    });
}

// Filter messages
function filterMessages() {
    const topic = topicFilter.value;
    let filtered = allMessages;

    if (topic) {
        filtered = filtered.filter(m => m.topic.includes(topic));
    }

    renderMessages(filtered);
}

// Render messages
function renderMessages(messages) {
    const container = document.getElementById('messages-container');

    if (messages.length === 0) {
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
        const topic = topicFilter.value;
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
}

// Utility functions
function formatDateTime(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Device Detail Page JavaScript

const API_BASE = '';
const DEVICE_ID = typeof DEVICE_ID !== 'undefined' ? DEVICE_ID :
    window.location.pathname.split('/').pop();

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
    loadAllData();
    setupEventListeners();
    startAutoRefresh();
});

// Event Listeners
function setupEventListeners() {
    const refreshBtn = getElement('refresh-btn');
    const topicFilter = getElement('topic-filter');
    const exportBtn = getElement('export-btn');

    if (refreshBtn) refreshBtn.addEventListener('click', loadAllData);
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
    try {
        const response = await fetch(`${API_BASE}/api/devices/${encodeURIComponent(DEVICE_ID)}`);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API error ${response.status}: ${errorText}`);
        }
        const data = await response.json();

        renderDeviceInfo(data.device);
        renderTopics(data.topic_counts);
        allMessages = data.recent_messages || [];
        allTopics = (data.topic_counts || []).map(t => t.topic.replace(`${DEVICE_ID}/`, ''));
        populateTopicFilter();
        filterMessages();
    } catch (error) {
        console.error('Failed to load device data:', error);
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
        statusBadge.textContent = device.status;
        statusBadge.className = `status-badge ${device.status}`;
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

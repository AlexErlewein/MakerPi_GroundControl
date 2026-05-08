// MakerPi GroundControl - Dashboard

const API_BASE = '';

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    loadStatus();
    setInterval(loadDashboardStats, 10000);
    setInterval(loadStatus, 5000);
});

async function loadDashboardStats() {
    try {
        const response = await fetch(`${API_BASE}/api/dashboard/stats`);
        if (!response.ok) return;
        const data = await response.json();

        const openLzEl = document.getElementById('open-laufzettel-count');
        const offlineDevEl = document.getElementById('offline-devices-count');
        const spendenEl = document.getElementById('spenden-current-month');
        const membersEl = document.getElementById('members-today');

        if (openLzEl) openLzEl.textContent = data.open_laufzettel_count || 0;
        if (offlineDevEl) offlineDevEl.textContent = data.offline_devices_count || 0;
        if (spendenEl) spendenEl.textContent = `€${(data.spenden_current_month || 0).toFixed(2)}`;
        if (membersEl) membersEl.textContent = data.members_today || 0;

        // Update system status indicators
        if (data.system_status) {
            updateStatusIndicator('docs', data.system_status.docs);
            updateStatusIndicator('zigbee', data.system_status.zigbee);
            updateStatusIndicator('databases', data.system_status.databases);
            updateStatusIndicator('gdrive', data.system_status.gdrive);

            // Make GDrive link clickable when connected
            const gdriveLink = document.getElementById('gdrive-link');
            const gdriveButton = document.getElementById('gdrive-button');
            if (gdriveLink && data.system_status.gdrive.status === 'ok') {
                // TODO: Add Google Drive URL when provided
                // For now, make it a span that shows as connected
                gdriveLink.style.cursor = 'pointer';
                gdriveLink.onclick = () => {
                    alert('Google Drive URL will be added later');
                };
                // Show button as well
                if (gdriveButton) {
                    gdriveButton.style.display = 'inline-block';
                    gdriveButton.onclick = () => {
                        alert('Google Drive URL will be added later');
                    };
                }
            }
        }
    } catch (error) {
        console.error('Failed to load dashboard stats:', error);
    }
}

function updateStatusIndicator(name, statusData) {
    const indicator = document.getElementById(`status-${name}`);
    const message = document.getElementById(`status-${name}-msg`);
    if (!indicator) return;

    indicator.textContent = '';
    indicator.className = 'status-indicator';

    if (statusData.status === 'ok') {
        indicator.classList.add('status-ok');
    } else if (statusData.status === 'error') {
        indicator.classList.add('status-error');
    } else if (statusData.status === 'warning') {
        indicator.classList.add('status-warning');
    } else {
        indicator.classList.add('status-unknown');
    }

    if (message) {
        message.textContent = statusData.message || '';
        message.title = statusData.message || '';
    }
}

async function loadStatus() {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    if (!statusDot || !statusText) return;
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
        statusDot.className = 'status-dot offline';
        statusText.textContent = 'Connection Error';
    }
}

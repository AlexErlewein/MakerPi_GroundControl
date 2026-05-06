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

        if (openLzEl) openLzEl.textContent = data.open_laufzettel_count || 0;
        if (offlineDevEl) offlineDevEl.textContent = data.offline_devices_count || 0;
    } catch (error) {
        console.error('Failed to load dashboard stats:', error);
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

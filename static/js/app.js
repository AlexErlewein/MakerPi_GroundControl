// MakerPi GroundControl - Dashboard (minimal MQTT status)

const API_BASE = '';

document.addEventListener('DOMContentLoaded', () => {
    loadStatus();
    setInterval(loadStatus, 5000);
});

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

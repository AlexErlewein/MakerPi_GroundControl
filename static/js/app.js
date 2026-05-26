// MakerPi GroundControl - Dashboard

const API_BASE = '';

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    checkDbHealth();
    setInterval(loadDashboardStats, 10000);
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
            updateStatusIndicator('gdrive', data.system_status.gdrive);

            // Make GDrive link clickable when connected
            const gdriveLink = document.getElementById('gdrive-link');
            if (gdriveLink && data.system_status.gdrive.status === 'ok') {
                // Use the Google Drive URL if available
                const gdriveUrl = data.system_status.gdrive.url || null;
                if (gdriveUrl) {
                    gdriveLink.style.cursor = 'pointer';
                    gdriveLink.onclick = () => {
                        window.open(gdriveUrl, '_blank');
                    };
                }
            } else if (gdriveLink) {
                gdriveLink.style.cursor = 'default';
                gdriveLink.onclick = null;
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

async function checkDbHealth() {
    const tiles = document.querySelectorAll('.db-tile');
    tiles.forEach(t => t.classList.add('db-checking'));
    try {
        const response = await fetch(`${API_BASE}/api/dashboard/db-health`);
        if (!response.ok) return;
        const data = await response.json();
        for (const db of data.databases) {
            const indicator = document.getElementById(`db-status-${db.name}`);
            const sizeEl = document.getElementById(`db-size-${db.name}`);
            if (indicator) {
                indicator.className = 'status-indicator';
                if (db.status === 'ok') indicator.classList.add('status-ok');
                else if (db.status === 'missing') indicator.classList.add('status-warning');
                else indicator.classList.add('status-error');
                indicator.title = db.message || '';
            }
            if (sizeEl) sizeEl.textContent = db.size || '';
        }
    } catch (error) {
        console.error('DB health check failed:', error);
    } finally {
        tiles.forEach(t => t.classList.remove('db-checking'));
    }
}

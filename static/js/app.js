// MakerPi GroundControl - Dashboard

const API_BASE = '';

function esc(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    loadActiveSessions();
    checkDbHealth();
    setInterval(loadDashboardStats, 10000);
    setInterval(loadActiveSessions, 10000);
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

// ── Active Device Sessions ─────────────────────────────────────

async function loadActiveSessions() {
    try {
        const response = await fetch('/api/dashboard/active-sessions');
        if (!response.ok) return;
        const data = await response.json();
        renderActiveSessions(data.active_sessions || []);
    } catch (error) {
        console.error('Failed to load active sessions:', error);
    }
}

function renderActiveSessions(sessions) {
    const section = document.getElementById('active-sessions-section');
    const container = document.getElementById('active-sessions-container');
    const countEl = document.getElementById('active-sessions-count');
    if (!section || !container) return;

    if (!sessions.length) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    if (countEl) countEl.textContent = `${sessions.length} aktiv`;

    container.innerHTML = sessions.map(s => {
        const startMs = new Date(s.start_time).getTime();
        const priceSuffix = s.pricing_model === 'per_hour' ? '/h' : '/min';
        const estPrice = s.unit_price != null
            ? (s.pricing_model === 'per_hour'
                ? ((Date.now() - startMs) / 3600000 * s.unit_price)
                : ((Date.now() - startMs) / 60000 * s.unit_price)
            ).toFixed(2)
            : '—';
        return `
            <div class="device-session-item" style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border:1px solid var(--border-color);border-radius:8px;margin-bottom:8px;background:var(--card-bg, #2a2a2a);">
                <div style="flex:1;min-width:0;">
                    <div style="font-weight:600;font-size:0.95rem;">${esc(s.device_name || s.device_id)}</div>
                    ${s.owner_name ? `<div style="color:var(--text-secondary);font-size:0.85rem;">${esc(s.owner_name)}</div>` : ''}
                    ${s.variante_name ? `<div style="color:var(--text-secondary);font-size:0.8rem;">${esc(s.variante_name)} ${s.unit_price != null ? `— ${s.unit_price.toFixed(2)}€${priceSuffix}` : ''}</div>` : ''}
                    <div style="font-size:0.8rem;color:var(--text-secondary);">Gestartet: ${new Date(s.start_time).toLocaleTimeString()}</div>
                </div>
                <div style="display:flex;align-items:center;gap:12px;flex-shrink:0;">
                    <div style="text-align:right;">
                        <div class="dash-session-duration" data-start-ms="${startMs}" style="font-family:monospace;font-size:1rem;font-weight:600;">—</div>
                        <div style="font-size:0.78rem;color:var(--text-secondary);">~ ${estPrice} €</div>
                    </div>
                    <button class="btn btn-sm btn-danger dash-session-stop-btn" data-device-id="${esc(s.device_id)}" data-session-id="${s.id}" style="padding:6px 12px;font-size:0.8rem;">Beenden</button>
                </div>
            </div>
        `;
    }).join('');

    container.querySelectorAll('.dash-session-stop-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const deviceId = btn.dataset.deviceId;
            const sessionId = btn.dataset.sessionId;
            if (!confirm('Gerätesitzung beenden und abrechnen?')) return;
            try {
                const stopRes = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/sessions/${sessionId}/stop`, {
                    method: 'POST',
                    credentials: 'include',
                });
                if (stopRes.ok) {
                    loadActiveSessions();
                } else {
                    const err = await stopRes.json();
                    alert('Fehler: ' + (err.detail || 'Beenden fehlgeschlagen'));
                }
            } catch (e) {
                alert('Fehler beim Beenden der Sitzung');
            }
        });
    });
}

// Live duration counter for dashboard sessions
setInterval(() => {
    document.querySelectorAll('.dash-session-duration').forEach(el => {
        const startMs = parseFloat(el.dataset.startMs);
        if (isNaN(startMs)) return;
        const elapsed = Math.floor((Date.now() - startMs) / 1000);
        const h = Math.floor(elapsed / 3600);
        const m = Math.floor((elapsed % 3600) / 60);
        const s = Math.floor(elapsed % 60);
        el.textContent = h > 0 ? `${h}h ${m}m` : `${m}m ${s}s`;
    });
}, 1000);

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

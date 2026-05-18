/**
 * Device Pairing - Token-based NFC scanner pairing
 * Manages pairing tokens in localStorage
 */

const PAIRING_TOKEN_KEY = 'device_pairing_token';
const PAIRED_DEVICE_KEY = 'paired_device_id';
const PAIRING_EXPIRES_KEY = 'pairing_expires_at';

/**
 * Load stored pairing token from localStorage
 * @returns {Object|null} Token data or null if not found/expired
 */
function loadStoredToken() {
    try {
        const token = localStorage.getItem(PAIRING_TOKEN_KEY);
        const deviceId = localStorage.getItem(PAIRED_DEVICE_KEY);
        const expiresAt = localStorage.getItem(PAIRING_EXPIRES_KEY);

        if (!token || !deviceId) {
            return null;
        }

        // Check expiration
        if (expiresAt) {
            const expiry = new Date(expiresAt);
            if (expiry < new Date()) {
                console.log('[DevicePairing] Token expired, clearing');
                clearToken();
                return null;
            }
        }

        return {
            token: token,
            deviceId: deviceId,
            expiresAt: expiresAt
        };
    } catch (e) {
        console.error('[DevicePairing] Error loading token:', e);
        return null;
    }
}

/**
 * Save pairing token to localStorage
 * @param {string} token - The pairing token
 * @param {string} deviceId - The paired device ID
 * @param {string|null} expiresAt - ISO datetime string or null for no expiry
 */
function saveToken(token, deviceId, expiresAt = null) {
    try {
        localStorage.setItem(PAIRING_TOKEN_KEY, token);
        localStorage.setItem(PAIRED_DEVICE_KEY, deviceId);
        if (expiresAt) {
            localStorage.setItem(PAIRING_EXPIRES_KEY, expiresAt);
        } else {
            localStorage.removeItem(PAIRING_EXPIRES_KEY);
        }
        console.log('[DevicePairing] Token saved for device:', deviceId);
    } catch (e) {
        console.error('[DevicePairing] Error saving token:', e);
    }
}

/**
 * Clear stored pairing token
 */
function clearToken() {
    try {
        localStorage.removeItem(PAIRING_TOKEN_KEY);
        localStorage.removeItem(PAIRED_DEVICE_KEY);
        localStorage.removeItem(PAIRING_EXPIRES_KEY);
        console.log('[DevicePairing] Token cleared');
    } catch (e) {
        console.error('[DevicePairing] Error clearing token:', e);
    }
}

/**
 * Validate a pairing token with the server
 * @param {string} token - Token to validate
 * @returns {Promise<Object>} Validation result
 */
async function validateToken(token) {
    try {
        const res = await fetch('/api/device-pairings/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pairing_token: token })
        });

        if (!res.ok) {
            return { valid: false, error: 'Validation failed' };
        }

        return await res.json();
    } catch (e) {
        console.error('[DevicePairing] Validation error:', e);
        return { valid: false, error: e.message };
    }
}

/**
 * Check if we have a valid token, clear if invalid
 * @returns {Promise<Object|null>} Valid token data or null
 */
async function getValidToken() {
    const stored = loadStoredToken();
    if (!stored) {
        return null;
    }

    // Re-validate with server
    const validation = await validateToken(stored.token);
    if (!validation.valid) {
        console.log('[DevicePairing] Token invalid, clearing:', validation.error);
        clearToken();
        return null;
    }

    return stored;
}

/**
 * Show token input modal
 * @param {Function} onSuccess - Callback when token is validated
 * @param {Function} onCancel - Callback when cancelled
 */
function showTokenInputModal(onSuccess, onCancel) {
    // Remove existing modal
    const existing = document.getElementById('device-pairing-modal');
    if (existing) {
        existing.remove();
    }

    const modal = document.createElement('div');
    modal.id = 'device-pairing-modal';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal" style="max-width: 400px;">
            <div class="modal-header">
                <h3>Gerät verbinden</h3>
                <button class="modal-close" id="pairing-modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <p>Geben Sie den Pairing-Token ein oder scannen Sie den QR-Code:</p>
                <input type="text" id="pairing-token-input" class="form-input"
                       placeholder="XXXX-XXXX-XXXX-XXXX" style="width: 100%; margin: 12px 0;">
                <div id="pairing-error" class="error-message" style="display: none; color: #f85149; margin-top: 8px;"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" id="pairing-cancel-btn">Abbrechen</button>
                <button class="btn btn-primary" id="pairing-connect-btn">Verbinden</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Event handlers
    document.getElementById('pairing-modal-close').addEventListener('click', () => {
        modal.remove();
        if (onCancel) onCancel();
    });

    document.getElementById('pairing-cancel-btn').addEventListener('click', () => {
        modal.remove();
        if (onCancel) onCancel();
    });

    document.getElementById('pairing-connect-btn').addEventListener('click', async () => {
        const input = document.getElementById('pairing-token-input');
        const errorDiv = document.getElementById('pairing-error');
        const token = input.value.trim().replace(/-/g, '');

        if (!token) {
            errorDiv.textContent = 'Bitte Token eingeben';
            errorDiv.style.display = 'block';
            return;
        }

        // Validate
        const validation = await validateToken(token);
        if (!validation.valid) {
            errorDiv.textContent = validation.error || 'Ungültiger Token';
            errorDiv.style.display = 'block';
            return;
        }

        // Save and close
        saveToken(token, validation.device_id, validation.expires_at);
        modal.remove();
        if (onSuccess) onSuccess(validation);
    });

    // Allow Enter key
    document.getElementById('pairing-token-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('pairing-connect-btn').click();
        }
    });
}

/**
 * Show connected device info with option to disconnect
 * @param {Object} tokenData - Current token data
 * @param {Function} onDisconnect - Callback when disconnected
 */
function showConnectedDeviceInfo(tokenData, onDisconnect) {
    const existing = document.getElementById('device-pairing-info');
    if (existing) {
        existing.remove();
    }

    const info = document.createElement('div');
    info.id = 'device-pairing-info';
    info.className = 'pairing-info';
    info.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; padding: 8px 12px;
                    background: #1a3a1a; border: 1px solid #238636; border-radius: 6px;
                    color: #3fb950; font-size: 0.9rem;">
            <span>Verbunden mit: <strong>${escapeHtml(tokenData.deviceId)}</strong></span>
            ${tokenData.expiresAt ? `<span class="text-muted">(läuft ab: ${new Date(tokenData.expiresAt).toLocaleString()})</span>` : ''}
            <button class="btn btn-sm btn-secondary" id="pairing-disconnect-btn" style="margin-left: auto;">Trennen</button>
        </div>
    `;

    // Insert at top of page or specific container
    const container = document.querySelector('.page-content') || document.body;
    container.insertBefore(info, container.firstChild);

    document.getElementById('pairing-disconnect-btn').addEventListener('click', () => {
        clearToken();
        info.remove();
        if (onDisconnect) onDisconnect();
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Initialize SSE stream for NFC scans with token
 * @param {string} token - Pairing token
 * @param {Object} options - Event handlers
 * @returns {EventSource} The SSE connection
 */
function startPairedScanStream(token, { onConfig, onScan, onError, onTimeout }) {
    const evtSource = new EventSource(`/api/scans/stream?token=${encodeURIComponent(token)}`);

    evtSource.addEventListener('config', (e) => {
        const data = JSON.parse(e.data);
        console.log('[DevicePairing] Config received:', data);
        if (onConfig) onConfig(data);
    });

    evtSource.addEventListener('error', (e) => {
        const data = JSON.parse(e.data);
        console.error('[DevicePairing] SSE error:', data);
        if (onError) onError(data.error);
        evtSource.close();
    });

    evtSource.addEventListener('timeout', () => {
        console.log('[DevicePairing] SSE timeout');
        if (onTimeout) onTimeout();
        evtSource.close();
    });

    evtSource.onmessage = (e) => {
        const data = JSON.parse(e.data);
        console.log('[DevicePairing] Scan received:', data);
        if (onScan) onScan(data);
    };

    evtSource.onerror = (e) => {
        console.error('[DevicePairing] SSE connection error:', e);
        if (onError) onError('Verbindungsfehler');
    };

    return evtSource;
}

// Export functions for use in other modules
window.DevicePairing = {
    loadStoredToken,
    saveToken,
    clearToken,
    validateToken,
    getValidToken,
    showTokenInputModal,
    showConnectedDeviceInfo,
    startPairedScanStream
};

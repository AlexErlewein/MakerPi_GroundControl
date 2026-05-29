let allMitglieder = [];
let enrollmentReaderId = "";
let activeScanSource = null;
let scanTimeout = null;
let nfcScanningMitgliedId = null;
let pairingToken = null;  // Device pairing token for NFC access
let pairedDeviceId = null;  // The specific device we're paired to

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

function esc(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

async function loadMitglieder() {
    const search = document.getElementById("filter-search").value.trim();
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    const res = await fetch(`/api/mitglieder?${params}`);
    allMitglieder = await res.json();
    render();
    updateStats();
}

function updateStats() {
    const total = allMitglieder.length;
    const withTag = allMitglieder.filter(m => m.nfc_uid).length;
    document.getElementById("total-count").textContent = total;
    document.getElementById("tag-count").textContent = withTag;
}

function render() {
    const tbody = document.getElementById("mitglieder-body");
    if (allMitglieder.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">Keine Mitglieder gefunden.</td></tr>';
        return;
    }
    tbody.innerHTML = allMitglieder.map(m => `
        <tr>
            <td><span class="member-id-badge">${esc(m.member_id)}</span></td>
            <td>${esc(m.name)}</td>
            <td>${m.email ? `<a href="mailto:${esc(m.email)}" class="email-link">${esc(m.email)}</a>` : '<span class="empty-cell">-</span>'}</td>
            <td>${m.phone ? esc(m.phone) : '<span class="empty-cell">-</span>'}</td>
            <td>${m.nfc_uid ? `<code class="uid">${esc(m.nfc_uid)}</code>` : '<span class="empty-cell">-</span>'}</td>
            <td>${m.login_username ? `<span class="login-badge" title="${esc(m.login_username)}">Login OK</span>` : '<span class="empty-cell">-</span>'}</td>
            <td>
                <div class="actions">
                    <button class="btn btn-sm btn-secondary" onclick="openDetails(${m.id})">Details</button>
                    <button class="btn btn-sm ${m.nfc_uid ? "btn-secondary" : "btn-success"}" onclick="openNfcScan(${m.id})">${m.nfc_uid ? "Tag bearbeiten" : "Tag registrieren"}</button>
                </div>
            </td>
        </tr>`).join("");
}

function setScanStatus(msg, type) {
    const el = document.getElementById("nfc-scan-status");
    if (!msg) { el.style.display = "none"; return; }
    el.style.display = "block";
    el.textContent = msg;
    el.style.background = type === "ok" ? "#1a3a1a" : type === "error" ? "#3a1a1a" : "#1a2a3a";
    el.style.color = type === "ok" ? "#3fb950" : type === "error" ? "#f85149" : "#79c0ff";
    el.style.border = `1px solid ${type === "ok" ? "#238636" : type === "error" ? "#da3633" : "#1f6feb"}`;
}

function resetScanButton() {
    const btn = document.getElementById("btn-scan-nfc");
    if (!btn) return;
    btn.textContent = "\uD83D\uDD13 Jetzt Scannen";
    btn.disabled = false;
    if (activeScanSource) { activeScanSource.close(); activeScanSource = null; }
    if (scanTimeout) { clearTimeout(scanTimeout); scanTimeout = null; }
}

async function startNfcScan() {
    console.log("[NFC] startNfcScan called, enrollmentReaderId:", enrollmentReaderId);
    const btn = document.getElementById("btn-scan-nfc");
    if (!btn) return;
    if (activeScanSource) {
        resetScanButton();
        setScanStatus(null);
        return;
    }

    // Try to load pairing token from localStorage (optional — not required)
    if (!pairingToken && window.DevicePairing) {
        const stored = window.DevicePairing.loadStoredToken();
        if (stored) {
            pairingToken = stored.token;
            pairedDeviceId = stored.deviceId;
            console.log("[NFC] Loaded pairing token for device:", pairedDeviceId);
        }
    }

    // Use paired device or fall back to configured enrollment reader
    const targetDevice = pairedDeviceId || enrollmentReaderId;
    if (!targetDevice && !pairingToken) {
        setScanStatus("Kein NFC-Reader konfiguriert. Bitte in den Geräte-Einstellungen einen Enrollment-Reader festlegen.", "error");
        return;
    }

    btn.textContent = "\u23F3 Warte auf Scan... (Abbrechen)";
    btn.disabled = false;
    setScanStatus(`Bereit – halte die Karte an den Reader "${targetDevice || pairedDeviceId}"...`, "info");

    // Build SSE URL — include token only if one is available
    const sseUrl = pairingToken
        ? `/api/scans/stream?token=${encodeURIComponent(pairingToken)}`
        : `/api/scans/stream`;
    console.log("[NFC] Opening SSE stream, paired:", !!pairingToken, "device:", targetDevice);
    const evtSource = new EventSource(sseUrl);
    activeScanSource = evtSource;
    let configuredReader = targetDevice;

    evtSource.addEventListener("config", (e) => {
        const data = JSON.parse(e.data);
        configuredReader = data.enrollment_reader_id || targetDevice;
        console.log("[NFC] config event received, configuredReader:", configuredReader, "paired:", data.paired);
    });

    evtSource.addEventListener("error", (e) => {
        const data = JSON.parse(e.data);
        console.error("[NFC] SSE error event:", data);
        evtSource.close();
        activeScanSource = null;
        resetScanButton();
        setScanStatus(`Fehler: ${data.error || 'Verbindung fehlgeschlagen'}`, "error");

        // Clear invalid token
        if (window.DevicePairing) {
            window.DevicePairing.clearToken();
        }
        pairingToken = null;
        pairedDeviceId = null;
    });

    evtSource.addEventListener("timeout", () => {
        console.log("[NFC] timeout event received");
        evtSource.close();
        activeScanSource = null;
        resetScanButton();
        setScanStatus("Timeout – kein Scan empfangen. Bitte erneut versuchen.", "error");
    });

    evtSource.onmessage = (e) => {
        console.log("[NFC] scan event received:", e.data);
        const data = JSON.parse(e.data);
        // With token, we only get events from our paired device, so no need to filter
        evtSource.close();
        activeScanSource = null;
        resetScanButton();
        const uid = data.uid.toUpperCase();
        document.getElementById("nfc-scan-uid").value = uid;
        setScanStatus(`✓ UID gescannt: ${uid} — sende Schreibbefehl…`, "info");
        enrollCard(uid);
    };

    evtSource.onerror = (e) => {
        console.error("[NFC] SSE error:", e);
        evtSource.close();
        activeScanSource = null;
        resetScanButton();
        setScanStatus("Verbindungsfehler beim Warten auf Scan.", "error");
    };
}

async function enrollCard(uid) {
    if (!nfcScanningMitgliedId) return;
    try {
        const res = await fetch(`/api/mitglieder/${nfcScanningMitgliedId}/enroll-card`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ uid }),
        });
        if (!res.ok) {
            const err = await res.json();
            setScanStatus(`Schreiben fehlgeschlagen: ${err.detail || "Unbekannter Fehler"}`, "error");
            return;
        }
        const data = await res.json();
        setScanStatus(`⏳ Schreibe auf Karte… halte die Karte weiter an den Reader.`, "info");
        pollWriteResult(data.device_id, data.request_id);
    } catch (e) {
        setScanStatus(`Fehler beim Schreiben: ${e.message}`, "error");
    }
}

async function pollWriteResult(deviceId, requestId, attempts = 0) {
    if (attempts > 35) {
        setScanStatus(`Timeout — kein Schreibergebnis erhalten. Bitte erneut versuchen.`, "error");
        return;
    }
    try {
        const res = await fetch(`/api/write-result?device_id=${encodeURIComponent(deviceId)}&request_id=${encodeURIComponent(requestId)}`);
        const data = await res.json();
        if (data.found) {
            if (data.success) {
                setScanStatus(`✓ Karte erfolgreich beschrieben! Jetzt Speichern klicken.`, "ok");
            } else {
                setScanStatus(`Fehler beim Beschreiben: ${data.error || "Unbekannter Fehler"}`, "error");
            }
            return;
        }
    } catch (e) {
        // ignore poll errors, keep retrying
    }
    setTimeout(() => pollWriteResult(deviceId, requestId, attempts + 1), 1000);
}

async function loadEnrollmentReader() {
    try {
        const res = await fetch("/api/settings/enrollment-reader");
        if (res.ok) {
            const data = await res.json();
            enrollmentReaderId = data.enrollment_reader_id || "";
            console.log("[NFC] enrollmentReaderId loaded:", enrollmentReaderId);
        } else {
            console.warn("[NFC] enrollment-reader endpoint returned:", res.status);
        }
    } catch (e) {
        console.warn("[NFC] Could not load enrollment reader config:", e);
    }
}


async function openDetails(id) {
    const m = allMitglieder.find(x => x.id === id);
    if (!m) return;
    try {
        const res = await fetch(`/api/mitglieder/${id}`);
        if (!res.ok) {
            alert("Fehler beim Laden der Details");
            return;
        }
        const details = await res.json();
        const content = document.getElementById("mitglied-details-content");
        content.innerHTML = `
            <form id="member-details-form" class="form-grid">
                <div class="form-group">
                    <label>Member-ID</label>
                    <input type="text" value="${esc(details.member_id || '')}" readonly disabled style="background: var(--bg-tertiary); color: var(--text-secondary); cursor: not-allowed;">
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <input type="text" value="${esc(details.status || 'Aktiv')}" readonly disabled style="background: var(--bg-tertiary); color: var(--text-secondary); cursor: not-allowed;">
                </div>
                <div class="form-group">
                    <label>Name</label>
                    <input type="text" id="detail-name" value="${esc(details.name || '')}" required>
                </div>
                <div class="form-group">
                    <label>E-Mail</label>
                    <input type="email" id="detail-email" value="${esc(details.email || '')}">
                </div>
                <div class="form-group">
                    <label>Telefon</label>
                    <input type="tel" id="detail-phone" value="${esc(details.phone || '')}">
                </div>
                <div style="display:flex;align-items:center;gap:8px;margin-top:12px;padding:10px 12px;background:var(--bg-tertiary);border-radius:6px;border:1px solid var(--border-color)">
                    <input type="checkbox" id="detail-sync-locked" ${details.sync_locked ? 'checked' : ''}>
                    <label for="detail-sync-locked" style="margin:0;cursor:pointer;">Von easyVerein-Sync ausgeschlossen</label>
                </div>
                <div class="form-group form-group-full" style="margin-top: 16px;">
                    <label>Notizen</label>
                    <textarea id="detail-notes" rows="4">${esc(details.notes || '')}</textarea>
                </div>
                <div class="modal-actions" style="margin-top: 20px; grid-column: 1 / -1;">
                    <button type="button" class="btn btn-secondary" onclick="closeDetailsModal()">Abbrechen</button>
                    <button type="button" class="btn btn-primary" onclick="saveMemberDetails(${id})">Speichern</button>
                </div>
            </form>
        `;
        document.getElementById("mitglied-details-modal").classList.remove("hidden");
    } catch (e) {
        console.error("Failed to load member details:", e);
        alert("Fehler beim Laden der Details");
    }
}

async function saveMemberDetails(id) {
    const name = document.getElementById("detail-name").value.trim();
    const email = document.getElementById("detail-email").value.trim();
    const phone = document.getElementById("detail-phone").value.trim();
    const notes = document.getElementById("detail-notes").value.trim();
    const syncLocked = document.getElementById("detail-sync-locked").checked;

    if (!name) {
        alert("Name ist erforderlich");
        return;
    }

    try {
        const res = await fetch(`/api/mitglieder/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, phone, notes, sync_locked: syncLocked }),
        });

        if (res.ok) {
            alert("✓ Änderungen gespeichert");
            await loadMitglieder();
            setTimeout(() => closeDetailsModal(), 1000);
        } else {
            const err = await res.json();
            alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen"));
        }
    } catch (e) {
        alert("Fehler: " + e.message);
    }
}

function openNfcScan(id) {
    const m = allMitglieder.find(x => x.id === id);
    if (!m) return;
    nfcScanningMitgliedId = id;
    const title = m.nfc_uid ? "Tag bearbeiten" : "Tag registrieren";
    document.getElementById("nfc-modal-title").textContent = title;
    document.getElementById("nfc-scan-uid").value = m.nfc_uid || "";
    setScanStatus(null);
    document.getElementById("nfc-scan-modal").classList.remove("hidden");
}

function closeNfcModal() {
    resetScanButton();
    setScanStatus(null);
    document.getElementById("nfc-scan-modal").classList.add("hidden");
    nfcScanningMitgliedId = null;
}

function closeDetailsModal() {
    document.getElementById("mitglied-details-modal").classList.add("hidden");
}

async function saveNfcUid() {
    if (!nfcScanningMitgliedId) return;
    const uid = document.getElementById("nfc-scan-uid").value.trim().toUpperCase() || null;
    if (!uid) {
        alert("Bitte eine NFC-UID eingeben oder scannen");
        return;
    }
    try {
        const res = await fetch(`/api/mitglieder/${nfcScanningMitgliedId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nfc_uid: uid }),
        });
        if (res.ok) {
            closeNfcModal();
            await loadMitglieder();
        } else {
            const err = await res.json();
            alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen"));
        }
    } catch (e) {
        alert("Fehler: " + e.message);
    }
}



async function loadSyncStatus() {
    try {
        const res = await fetch("/api/mitglieder/sync-status");
        if (!res.ok) return;
        const status = await res.json();
        
        const statusEl = document.getElementById("sync-status");
        const lastEl = document.getElementById("sync-last");
        
        if (status.last_sync) {
            const date = new Date(status.last_sync);
            lastEl.textContent = date.toLocaleString("de-DE");
            
            if (status.success) {
                statusEl.textContent = "✓ OK";
                statusEl.style.color = "#238636";
            } else {
                statusEl.textContent = "✗ Fehler";
                statusEl.style.color = "#da3633";
            }
        } else {
            statusEl.textContent = "-";
            lastEl.textContent = "Noch nie synchronisiert";
        }
    } catch (e) {
        console.error("Failed to load sync status:", e);
    }
}

async function triggerEasyVereinSync() {
    const btn = document.getElementById("sync-easyverein-btn");
    const statusEl = document.getElementById("sync-status");
    const lastEl = document.getElementById("sync-last");
    
    btn.disabled = true;
    btn.innerHTML = '<span class="btn-icon">⏳</span> Sync läuft...';
    statusEl.textContent = "⏳";
    
    try {
        const res = await fetch("/api/mitglieder/sync", { method: "POST" });
        const result = await res.json();
        
        if (result.success) {
            alert(`Synchronisation erfolgreich!\nNeu: ${result.created}\nAktualisiert: ${result.updated}`);
            await loadMitglieder();
        } else {
            alert(`Synchronisation fehlgeschlagen:\n${result.message}`);
        }
    } catch (e) {
        alert("Fehler bei der Synchronisation. Bitte versuchen Sie es später erneut.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🔄</span> easyVerein Sync';
        await loadSyncStatus();
    }
}

document.getElementById("clear-btn").addEventListener("click", () => {
    document.getElementById("filter-search").value = "";
    loadMitglieder();
});
document.getElementById("filter-search").addEventListener("input", debounce(() => {
    loadMitglieder();
}, 300));
document.getElementById("sync-easyverein-btn").addEventListener("click", triggerEasyVereinSync);
document.getElementById("sync-status-card").addEventListener("click", loadSyncStatus);

// Details modal event listeners
document.getElementById("details-modal-close").addEventListener("click", closeDetailsModal);
document.getElementById("details-modal-overlay").addEventListener("click", closeDetailsModal);

// NFC scan modal event listeners
document.getElementById("nfc-modal-close").addEventListener("click", closeNfcModal);
document.getElementById("nfc-modal-overlay").addEventListener("click", closeNfcModal);
document.getElementById("nfc-cancel-btn").addEventListener("click", closeNfcModal);
document.getElementById("btn-scan-nfc").addEventListener("click", startNfcScan);
document.getElementById("nfc-save-btn").addEventListener("click", saveNfcUid);

loadMitglieder();
loadSyncStatus();
loadEnrollmentReader();

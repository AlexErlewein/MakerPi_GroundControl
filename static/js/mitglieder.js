let allMitglieder = [];
let enrollmentReaderId = "";
let activeScanSource = null;
let scanTimeout = null;
let nfcScanningMitgliedId = null;

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
        tbody.innerHTML = '<tr><td colspan="7" class="empty">Keine Mitglieder gefunden.</td></tr>';
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
                    <button class="btn btn-sm btn-danger" onclick="deleteMitglied(${m.id})">Löschen</button>
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

function startNfcScan() {
    console.log("[NFC] startNfcScan called, enrollmentReaderId:", enrollmentReaderId);
    const btn = document.getElementById("btn-scan-nfc");
    if (!btn) return;
    if (activeScanSource) {
        resetScanButton();
        setScanStatus(null);
        return;
    }
    if (!enrollmentReaderId) {
        setScanStatus("Kein Enrollment-Reader konfiguriert. Bitte zuerst im Dashboard einstellen.", "error");
        console.warn("[NFC] No enrollment reader configured!");
        return;
    }
    btn.textContent = "\u23F3 Warte auf Scan... (Abbrechen)";
    btn.disabled = false;
    setScanStatus(`Bereit – halte die Karte an den Reader "${enrollmentReaderId}"...`, "info");

    console.log("[NFC] Opening SSE stream /api/scans/stream");
    const evtSource = new EventSource("/api/scans/stream");
    activeScanSource = evtSource;
    let configuredReader = enrollmentReaderId;

    evtSource.addEventListener("config", (e) => {
        const data = JSON.parse(e.data);
        configuredReader = data.enrollment_reader_id || enrollmentReaderId;
        console.log("[NFC] config event received, configuredReader:", configuredReader);
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
        if (data.device_id !== configuredReader) {
            console.log("[NFC] device_id mismatch:", data.device_id, "!=", configuredReader);
            return;
        }
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
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
                <div>
                    <strong>Member-ID:</strong><br>
                    ${esc(details.member_id || "-")}
                </div>
                <div>
                    <strong>Name:</strong><br>
                    ${esc(details.name || "-")}
                </div>
                <div>
                    <strong>E-Mail:</strong><br>
                    ${details.email ? `<a href="mailto:${esc(details.email)}">${esc(details.email)}</a>` : "-"}
                </div>
                <div>
                    <strong>Telefon:</strong><br>
                    ${esc(details.phone || "-")}
                </div>
                <div>
                    <strong>NFC-UID:</strong><br>
                    ${details.nfc_uid ? `<code class="uid">${esc(details.nfc_uid)}</code>` : "-"}
                </div>
                <div>
                    <strong>Login-Username:</strong><br>
                    ${esc(details.login_username || "-")}
                </div>
            </div>
            <div style="margin-top: 16px;">
                <strong>Notizen:</strong><br>
                ${esc(details.notes || "-")}
            </div>
            <div style="margin-top: 20px; padding: 12px; background: var(--bg-tertiary, #161b22); border: 1px solid var(--border, #30363d); border-radius: 6px;">
                <h4 style="margin: 0 0 8px 0; color: var(--text-secondary, #8b949e);">Verfügbare Geräte</h4>
                <p style="margin: 0; color: var(--text-secondary, #8b949e); font-size: 0.9rem;">Noch nicht implementiert</p>
            </div>
        `;
        document.getElementById("mitglied-details-modal").classList.remove("hidden");
    } catch (e) {
        console.error("Failed to load member details:", e);
        alert("Fehler beim Laden der Details");
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

async function deleteMitglied(id) {
    const m = allMitglieder.find(x => x.id === id);
    if (!confirm('Mitglied "' + (m ? m.name : id) + '" wirklich löschen?')) return;
    const res = await fetch(`/api/mitglieder/${id}`, { method: "DELETE" });
    if (res.ok) {
        await loadMitglieder();
    } else {
        const err = await res.json();
        alert("Fehler: " + (err.detail || "Löschen fehlgeschlagen"));
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

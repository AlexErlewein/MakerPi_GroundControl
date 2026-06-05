let allTags = [];
let allScans = [];
let editingUid = null;

// NFC Enrollment variables
let enrollmentReaderId = "";
let activeScanSource = null;
let scanTimeout = null;
let selectedMemberId = null;
let scannedUid = null;
let pairingToken = null;
let pairedDeviceId = null;

async function loadTags() {
    const res = await fetch("/api/tags");
    allTags = await res.json();
    renderTags();
    document.getElementById("tag-count").textContent = allTags.length;
}

async function loadScans() {
    const res = await fetch("/api/scans?limit=100");
    allScans = await res.json();
    renderScans();
    document.getElementById("scan-count").textContent = allScans.length;
    const unknown = allScans.filter((s) => !s.validated).length;
    document.getElementById("unknown-count").textContent = unknown;
}

function filterRows(inputId, tbodyId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const needle = input.value.trim().toLowerCase();
    document.querySelectorAll(`#${tbodyId} tr`).forEach(tr => {
        tr.style.display = !needle || tr.textContent.toLowerCase().includes(needle) ? "" : "none";
    });
}

function renderTags() {
    const tbody = document.getElementById("tags-body");
    if (allTags.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty">No tags registered yet.</td></tr>';
        return;
    }
    tbody.innerHTML = allTags
        .map(
            (tag) => `
        <tr>
            <td><code class="uid">${tag.uid}</code></td>
            <td>${esc(tag.owner_name)}</td>
            <td>${esc(tag.owner_email || "")}</td>
            <td class="notes-cell">${esc(tag.notes || "")}</td>
            <td>${
                tag.active
                    ? '<span class="badge badge-ok">Active</span>'
                    : '<span class="badge badge-off">Disabled</span>'
            }</td>
            <td>${formatDate(tag.created_at)}</td>
            <td class="actions">
                ${tag.source === "mitglied"
                    ? `<span class="badge badge-ok" title="Enrolled via Mitglieder">Mitglied</span>`
                    : `<button class="btn btn-sm btn-secondary" onclick="openEdit('${tag.uid}')">Edit</button>
                       <button class="btn btn-sm btn-danger" onclick="deleteTag('${tag.uid}')">Delete</button>`
                }
            </td>
        </tr>
    `,
        )
        .join("");
    filterRows("tags-search", "tags-body");
}

function renderScans() {
    const tbody = document.getElementById("scans-body");
    if (allScans.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="empty">No scans recorded yet.</td></tr>';
        return;
    }
    tbody.innerHTML = allScans
        .map((scan) => {
            const isUnknown = !scan.validated;
            const registerBtn = isUnknown
                ? `<button class="btn btn-sm btn-success" onclick="openAddFromScan('${scan.uid}')">+ Register</button>`
                : "";
            const cardParts = [];
            if (scan.card_name) cardParts.push(esc(scan.card_name));
            if (scan.card_member_id) cardParts.push('<small>ID: ' + esc(scan.card_member_id) + '</small>');
            if (scan.card_email) cardParts.push('<small>' + esc(scan.card_email) + '</small>');
            const cardDataHtml = cardParts.length
                ? '<span class="badge badge-ok">GNDCTRL</span> ' + cardParts.join('<br>')
                : '<span class="muted">-</span>';
            return `
        <tr class="${isUnknown ? "row-unknown" : ""}">
            <td>${formatDate(scan.timestamp)}</td>
            <td>${
                scan.validated
                    ? '<span class="badge badge-ok">✓ Valid</span>'
                    : '<span class="badge badge-unknown">✗ Unknown</span>'
            }</td>
            <td><a href="/devices/${scan.device_id}">${esc(scan.device_id)}</a></td>
            <td>${esc(scan.owner_name || "-")}</td>
            <td><code class="uid">${scan.uid}</code></td>
            <td>${esc(scan.tag_type || "-")}</td>
            <td><code>${esc(scan.atqa || "-")}</code></td>
            <td><code>${esc(scan.sak || "-")}</code></td>
            <td>${cardDataHtml}</td>
            <td>${esc(scan.member_id || "-")}</td>
            <td>${esc(scan.member_name || "-")}</td>
            <td>${registerBtn}</td>
        </tr>`;
        })
        .join("");
    filterRows("scans-search", "scans-body");
}

function esc(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function formatDate(iso) {
    if (!iso) return "-";
    const d = new Date(iso);
    return d.toLocaleString();
}

function openAddFromScan(uid) {
    const alreadyRegistered = allTags.find((t) => t.uid === uid);
    if (alreadyRegistered) {
        openEdit(uid);
        return;
    }
    openAdd();
    document.getElementById("field-uid").value = uid;
}

function openAdd() {
    editingUid = null;
    document.getElementById("modal-title").textContent = "Add Tag";
    document.getElementById("tag-form").reset();
    document.getElementById("field-uid").disabled = false;
    document.getElementById("field-active").checked = true;
    document.getElementById("tag-modal").classList.remove("hidden");
}

function openEdit(uid) {
    const tag = allTags.find((t) => t.uid === uid);
    if (!tag) return;
    editingUid = uid;
    document.getElementById("modal-title").textContent = "Edit Tag";
    document.getElementById("field-uid").value = tag.uid;
    document.getElementById("field-uid").disabled = true;
    document.getElementById("field-owner").value = tag.owner_name || "";
    document.getElementById("field-member-id").value = tag.member_id || "";
    document.getElementById("field-email").value = tag.owner_email || "";
    document.getElementById("field-notes").value = tag.notes || "";
    document.getElementById("field-active").checked = tag.active;
    document.getElementById("tag-modal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("tag-modal").classList.add("hidden");
}

async function deleteTag(uid) {
    if (!confirm(`Delete tag ${uid}? This cannot be undone.`)) return;
    const res = await fetch(`/api/tags/${uid}`, { method: "DELETE" });
    if (res.ok) {
        await loadTags();
    } else {
        const err = await res.json();
        alert("Error: " + (err.detail || "Failed to delete tag"));
    }
}

document.getElementById("tag-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
        uid: document.getElementById("field-uid").value.trim().toUpperCase(),
        owner_name: document.getElementById("field-owner").value.trim(),
        member_id: document.getElementById("field-member-id").value.trim() || null,
        owner_email: document.getElementById("field-email").value.trim() || null,
        notes: document.getElementById("field-notes").value.trim() || null,
        active: document.getElementById("field-active").checked,
    };

    let res;
    if (editingUid) {
        res = await fetch(`/api/tags/${editingUid}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    } else {
        res = await fetch("/api/tags", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    }

    if (res.ok) {
        closeModal();
        await loadTags();
    } else {
        const err = await res.json();
        alert("Error: " + (err.detail || "Failed to save tag"));
    }
});

document.getElementById("add-tag-btn").addEventListener("click", openNfcEnroll);
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("cancel-btn").addEventListener("click", closeModal);
document.getElementById("modal-overlay").addEventListener("click", closeModal);
document.getElementById("tags-search").addEventListener("input", () => filterRows("tags-search", "tags-body"));
document.getElementById("scans-search").addEventListener("input", () => filterRows("scans-search", "scans-body"));

// NFC Enrollment modal event listeners
document.getElementById("nfc-enroll-close").addEventListener("click", closeNfcEnroll);
document.getElementById("nfc-enroll-overlay").addEventListener("click", closeNfcEnroll);
document.getElementById("nfc-enroll-cancel").addEventListener("click", closeNfcEnroll);
document.getElementById("member-search-btn").addEventListener("click", searchMembers);
document.getElementById("member-search-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") searchMembers();
});
document.getElementById("btn-enroll-scan").addEventListener("click", startNfcScan);
document.getElementById("nfc-enroll-save").addEventListener("click", saveEnrolledTag);

loadTags();
loadScans();
loadEnrollmentReader();

// ── NFC Enrollment Functions ─────────────────────────────────────────────────

async function loadEnrollmentReader() {
    try {
        const res = await fetch("/api/settings/enrollment-reader");
        if (res.ok) {
            const data = await res.json();
            enrollmentReaderId = data.enrollment_reader_id || "";
        }
    } catch (e) {
        console.error("Failed to load enrollment reader:", e);
    }
}

function openNfcEnroll() {
    selectedMemberId = null;
    scannedUid = null;
    document.getElementById("nfc-enroll-title").textContent = "Tag registrieren";
    document.getElementById("member-search-input").value = "";
    document.getElementById("member-search-results").style.display = "none";
    document.getElementById("selected-member-info").style.display = "none";
    document.getElementById("nfc-enroll-uid").value = "";
    document.getElementById("nfc-enroll-save").disabled = true;
    setEnrollStatus(null);
    document.getElementById("nfc-enroll-modal").classList.remove("hidden");
}

function closeNfcEnroll() {
    resetScanButton();
    setEnrollStatus(null);
    document.getElementById("nfc-enroll-modal").classList.add("hidden");
    selectedMemberId = null;
    scannedUid = null;
}

async function searchMembers() {
    const query = document.getElementById("member-search-input").value.trim();
    if (!query) return;

    try {
        const res = await fetch(`/api/mitglieder?search=${encodeURIComponent(query)}`);
        if (!res.ok) throw new Error("Search failed");
        const members = await res.json();

        const resultsDiv = document.getElementById("member-search-results");
        if (members.length === 0) {
            resultsDiv.innerHTML = '<div style="padding: 8px; color: #8b949e;">Keine Mitglieder gefunden</div>';
        } else {
            resultsDiv.innerHTML = members.map(m => `
                <div class="member-result" data-id="${m.id}" data-name="${esc(m.name)}"
                     style="padding: 8px 10px; cursor: pointer; border-bottom: 1px solid var(--border, #30363d);
                            transition: background 0.2s;"
                     onmouseover="this.style.background='var(--hover-bg, #21262d)'"
                     onmouseout="this.style.background='transparent'">
                    <strong>${esc(m.name)}</strong>
                    ${m.member_id ? `<span style="color: #8b949e; margin-left: 8px;">(${esc(m.member_id)})</span>` : ""}
                    ${m.nfc_uid ? `<span style="color: #3fb950; margin-left: 8px;">✓ hat bereits Tag</span>` : ""}
                </div>
            `).join("");

            // Add click handlers
            resultsDiv.querySelectorAll(".member-result").forEach(el => {
                el.addEventListener("click", () => selectMember(
                    parseInt(el.dataset.id),
                    el.dataset.name
                ));
            });
        }
        resultsDiv.style.display = "block";
    } catch (e) {
        console.error("Member search failed:", e);
        setEnrollStatus("Fehler bei der Mitgliedersuche", "error");
    }
}

function selectMember(id, name) {
    selectedMemberId = id;
    document.getElementById("selected-member-id").value = id;
    document.getElementById("selected-member-name").textContent = name;
    document.getElementById("selected-member-info").style.display = "block";
    document.getElementById("member-search-results").style.display = "none";
    document.getElementById("member-search-input").value = name;
    updateSaveButton();
}

function setEnrollStatus(msg, type) {
    const el = document.getElementById("nfc-enroll-status");
    if (!msg) { el.style.display = "none"; return; }
    el.style.display = "block";
    el.textContent = msg;
    el.style.background = type === "ok" ? "#1a3a1a" : type === "error" ? "#3a1a1a" : "#1a2a3a";
    el.style.color = type === "ok" ? "#3fb950" : type === "error" ? "#f85149" : "#79c0ff";
    el.style.border = `1px solid ${type === "ok" ? "#238636" : type === "error" ? "#da3633" : "#1f6feb"}`;
}

function resetScanButton() {
    const btn = document.getElementById("btn-enroll-scan");
    if (!btn) return;
    btn.textContent = "🔑 Jetzt Scannen";
    btn.disabled = false;
    if (activeScanSource) { activeScanSource.close(); activeScanSource = null; }
    if (scanTimeout) { clearTimeout(scanTimeout); scanTimeout = null; }
}

async function startNfcScan() {
    if (!selectedMemberId) {
        setEnrollStatus("Bitte zuerst ein Mitglied auswählen", "error");
        return;
    }

    const btn = document.getElementById("btn-enroll-scan");
    if (!btn) return;

    // Check for stored pairing token first
    if (window.DevicePairing) {
        const tokenData = await window.DevicePairing.getValidToken();
        if (tokenData) {
            pairingToken = tokenData.token;
            pairedDeviceId = tokenData.deviceId;
        }
    }

    const targetDevice = pairedDeviceId || enrollmentReaderId;
    if (!targetDevice && !pairingToken) {
        setEnrollStatus("Kein NFC-Reader konfiguriert. Bitte in den Geräte-Einstellungen einen Reader festlegen.", "error");
        return;
    }

    btn.textContent = "⏳ Scannen...";
    btn.disabled = true;
    setEnrollStatus("NFC-Reader bereit. Halten Sie die Karte an den Reader...", "info");

    // Use paired scan stream if we have a token
    if (pairingToken && window.DevicePairing) {
        activeScanSource = window.DevicePairing.startPairedScanStream(pairingToken, {
            onConfig: (data) => {
                setEnrollStatus(`Reader bereit: ${data.device_id}`, "info");
            },
            onScan: (data) => {
                handleScanComplete(data);
            },
            onError: (err) => {
                setEnrollStatus("Fehler: " + err, "error");
                resetScanButton();
            },
            onTimeout: () => {
                setEnrollStatus("Zeitüberschreitung. Bitte erneut versuchen.", "error");
                resetScanButton();
            }
        });
    } else {
        // Fallback to legacy SSE stream
        const url = `/api/scans/stream?device_id=${encodeURIComponent(targetDevice)}`;
        const evtSource = new EventSource(url);
        activeScanSource = evtSource;

        evtSource.addEventListener("config", (e) => {
            const data = JSON.parse(e.data);
            setEnrollStatus(`Reader bereit: ${data.device_id}`, "info");
        });

        evtSource.addEventListener("scan", (e) => {
            const data = JSON.parse(e.data);
            handleScanComplete(data);
        });

        evtSource.addEventListener("error", (e) => {
            const data = JSON.parse(e.data);
            setEnrollStatus("Fehler: " + (data.error || "Unbekannter Fehler"), "error");
            resetScanButton();
        });

        evtSource.addEventListener("timeout", () => {
            setEnrollStatus("Zeitüberschreitung. Bitte erneut versuchen.", "error");
            resetScanButton();
        });

        evtSource.onerror = () => {
            setEnrollStatus("Verbindungsfehler zum Reader", "error");
            resetScanButton();
        };
    }

    // Set timeout
    scanTimeout = setTimeout(() => {
        if (activeScanSource) {
            activeScanSource.close();
            activeScanSource = null;
        }
        resetScanButton();
        setEnrollStatus("Zeitüberschreitung. Bitte erneut versuchen.", "error");
    }, 30000);
}

async function handleScanComplete(data) {
    if (activeScanSource) {
        activeScanSource.close();
        activeScanSource = null;
    }
    if (scanTimeout) {
        clearTimeout(scanTimeout);
        scanTimeout = null;
    }
    resetScanButton();

    const uid = data.uid.toUpperCase();
    scannedUid = uid;
    document.getElementById("nfc-enroll-uid").value = uid;
    setEnrollStatus(`✓ UID gescannt: ${uid} — sende Schreibbefehl...`, "info");

    // Write card data
    await writeCardData(uid);
}

async function writeCardData(uid) {
    if (!selectedMemberId) return;

    try {
        // First write to the card via the writer endpoint
        const writeRes = await fetch(`/api/mitglieder/${selectedMemberId}/enroll-card`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ uid }),
        });

        if (!writeRes.ok) {
            const err = await writeRes.json();
            setEnrollStatus(`Fehler beim Beschreiben: ${err.detail || "Unbekannter Fehler"}`, "error");
            return;
        }

        const writeData = await writeRes.json();

        if (writeData.found) {
            if (writeData.success) {
                setEnrollStatus(`✓ Karte erfolgreich beschrieben!`, "ok");
                // Provision login (set card data)
                await provisionLogin();
            } else {
                setEnrollStatus(`Fehler beim Beschreiben: ${writeData.error || "Unbekannter Fehler"}`, "error");
            }
        } else {
            setEnrollStatus("Kein Writer-Gerät gefunden", "error");
        }
    } catch (e) {
        console.error("Card write error:", e);
        setEnrollStatus("Verbindungsfehler beim Beschreiben", "error");
    }
}

async function provisionLogin() {
    if (!selectedMemberId) return;

    try {
        const res = await fetch(`/api/mitglieder/${selectedMemberId}/provision-login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });

        const data = await res.json();

        if (res.ok && data.success) {
            setEnrollStatus(`✓ Karte vollständig registriert! Sie können jetzt speichern.`, "ok");
            updateSaveButton();
        } else {
            setEnrollStatus(`Fehler bei der Bereitstellung: ${data.error || "Unbekannter Fehler"}`, "error");
        }
    } catch (e) {
        console.error("Provision error:", e);
        setEnrollStatus("Fehler bei der Bereitstellung", "error");
    }
}

function updateSaveButton() {
    const saveBtn = document.getElementById("nfc-enroll-save");
    saveBtn.disabled = !(selectedMemberId && scannedUid);
}

async function saveEnrolledTag() {
    if (!selectedMemberId || !scannedUid) return;

    const saveBtn = document.getElementById("nfc-enroll-save");
    saveBtn.disabled = true;

    try {
        // Update member with NFC UID
        const res = await fetch(`/api/mitglieder/${selectedMemberId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nfc_uid: scannedUid }),
        });

        if (res.ok) {
            setEnrollStatus("✓ Tag erfolgreich registriert!", "ok");
            setTimeout(() => {
                closeNfcEnroll();
                loadTags(); // Refresh tags list
            }, 1000);
        } else {
            const err = await res.json();
            setEnrollStatus(`Fehler: ${err.detail || "Speichern fehlgeschlagen"}`, "error");
            saveBtn.disabled = false;
        }
    } catch (e) {
        console.error("Save error:", e);
        setEnrollStatus("Verbindungsfehler", "error");
        saveBtn.disabled = false;
    }
}

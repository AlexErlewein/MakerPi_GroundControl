let allTags = [];
let allScans = [];
let editingUid = null;

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
                <button class="btn btn-sm btn-secondary" onclick="openEdit('${tag.uid}')">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deleteTag('${tag.uid}')">Delete</button>
            </td>
        </tr>
    `,
        )
        .join("");
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

document.getElementById("add-tag-btn").addEventListener("click", openAdd);
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("cancel-btn").addEventListener("click", closeModal);
document.getElementById("modal-overlay").addEventListener("click", closeModal);
document.getElementById("refresh-btn").addEventListener("click", () => {
    loadTags();
    loadScans();
});

loadTags();
loadScans();

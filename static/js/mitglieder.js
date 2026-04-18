let allMitglieder = [];
let editingId = null;

function esc(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

async function loadMitglieder() {
    const search = document.getElementById("filter-search").value.trim();
    const status = document.getElementById("filter-status").value;
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    const res = await fetch(`/api/mitglieder?${params}`);
    allMitglieder = await res.json();
    render();
    updateStats();
}

function updateStats() {
    const active = allMitglieder.filter(m => m.status === "active").length;
    const inactive = allMitglieder.filter(m => m.status === "inactive").length;
    document.getElementById("total-count").textContent = allMitglieder.length;
    document.getElementById("active-count").textContent = active;
    document.getElementById("inactive-count").textContent = inactive;
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
            <td><span class="status-badge ${m.status === "active" ? "active" : "inactive"}">${m.status === "active" ? "Aktiv" : "Inaktiv"}</span></td>
            <td>${m.joined_date ? new Date(m.joined_date).toLocaleDateString("de-DE") : '<span class="empty-cell">-</span>'}</td>
            <td class="actions">
                <button class="btn btn-sm btn-secondary" onclick="openEdit(${m.id})">Bearbeiten</button>
                <button class="btn btn-sm btn-danger" onclick="deleteMitglied(${m.id})">Löschen</button>
            </td>
        </tr>`).join("");
}

function openAdd() {
    editingId = null;
    document.getElementById("modal-title").textContent = "Neues Mitglied";
    document.getElementById("mitglied-form").reset();
    document.getElementById("mitglied-modal").classList.remove("hidden");
}

function openEdit(id) {
    const m = allMitglieder.find(x => x.id === id);
    if (!m) return;
    editingId = id;
    document.getElementById("modal-title").textContent = "Mitglied bearbeiten";
    document.getElementById("f-member-id").value = m.member_id || "";
    document.getElementById("f-name").value = m.name || "";
    document.getElementById("f-email").value = m.email || "";
    document.getElementById("f-phone").value = m.phone || "";
    document.getElementById("f-status").value = m.status || "active";
    document.getElementById("f-joined").value = m.joined_date || "";
    document.getElementById("f-notes").value = m.notes || "";
    document.getElementById("mitglied-modal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("mitglied-modal").classList.add("hidden");
}

async function deleteMitglied(id) {
    const m = allMitglieder.find(x => x.id === id);
    if (!confirm(`Mitglied "${m?.name}" wirklich löschen?`)) return;
    const res = await fetch(`/api/mitglieder/${id}`, { method: "DELETE" });
    if (res.ok) {
        await loadMitglieder();
    } else {
        const err = await res.json();
        alert("Fehler: " + (err.detail || "Löschen fehlgeschlagen"));
    }
}

document.getElementById("mitglied-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
        member_id: document.getElementById("f-member-id").value.trim(),
        name: document.getElementById("f-name").value.trim(),
        email: document.getElementById("f-email").value.trim() || null,
        phone: document.getElementById("f-phone").value.trim() || null,
        status: document.getElementById("f-status").value,
        joined_date: document.getElementById("f-joined").value || null,
        notes: document.getElementById("f-notes").value.trim() || null,
    };
    const url = editingId ? `/api/mitglieder/${editingId}` : "/api/mitglieder";
    const method = editingId ? "PUT" : "POST";
    const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (res.ok) {
        closeModal();
        await loadMitglieder();
    } else {
        const err = await res.json();
        alert("Fehler: " + (err.detail || "Speichern fehlgeschlagen"));
    }
});

document.getElementById("new-mitglied-btn").addEventListener("click", openAdd);
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("cancel-btn").addEventListener("click", closeModal);
document.getElementById("modal-overlay").addEventListener("click", closeModal);
document.getElementById("refresh-btn").addEventListener("click", loadMitglieder);
document.getElementById("filter-btn").addEventListener("click", loadMitglieder);
document.getElementById("clear-btn").addEventListener("click", () => {
    document.getElementById("filter-search").value = "";
    document.getElementById("filter-status").value = "";
    loadMitglieder();
});
document.getElementById("filter-search").addEventListener("keydown", (e) => {
    if (e.key === "Enter") loadMitglieder();
});

loadMitglieder();

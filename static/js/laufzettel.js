let allEntries = [];
let allTags = [];
let allMitglieder = [];

async function loadMitglieder() {
    try {
        const res = await fetch("/api/mitglieder?status=active");
        allMitglieder = await res.json();
        const sel = document.getElementById("new-lz-member-select");
        sel.innerHTML = '<option value="">— Manuell eingeben —</option>';
        allMitglieder.forEach((m) => {
            const opt = document.createElement("option");
            opt.value = m.id;
            opt.textContent = m.name + (m.member_id ? " (" + m.member_id + ")" : "");
            sel.appendChild(opt);
        });
    } catch(e) { console.warn("loadMitglieder failed", e); }
}

async function loadTags() {
    try {
        const res = await fetch("/api/tags");
        allTags = await res.json();
        const dl = document.getElementById("uid-suggestions");
        dl.innerHTML = allTags
            .map(function(t) {
                return '<option value="' + t.uid + '">' + (t.owner_name || "") + (t.member_id ? " (" + t.member_id + ")" : "") + "</option>";
            })
            .join("");
    } catch(e) { console.warn("loadTags failed", e); }
}

async function loadLaufzettel() {
    try {
        const uid = document.getElementById("filter-name").value.trim();
        const date = document.getElementById("filter-date").value;

        let url = "/api/laufzettel";
        const params = new URLSearchParams();
        if (date) params.set("date", date);
        if (params.toString()) url += "?" + params.toString();

        const res = await fetch(url);
        allEntries = await res.json();

        if (uid) {
            const q = uid.toLowerCase();
            allEntries = allEntries.filter(
                (e) =>
                    (e.owner_name || "").toLowerCase().includes(q) ||
                    (e.uid || "").toLowerCase().includes(q) ||
                    (e.member_id || "").toLowerCase().includes(q)
            );
        }

        renderStats();
        renderTable();
    } catch(e) { console.warn("loadLaufzettel failed", e); }
}

function renderStats() {
    document.getElementById("total-count").textContent = allEntries.length;

    const today = new Date().toISOString().slice(0, 10);
    const todayCount = allEntries.filter((e) => e.date === today).length;
    document.getElementById("today-count").textContent = todayCount;

    const unique = new Set(allEntries.map((e) => e.uid)).size;
    document.getElementById("cardholder-count").textContent = unique;

    const paid = allEntries.filter((e) => e.payment_method).length;
    document.getElementById("paid-count").textContent = paid;
}

function renderTable() {
    const tbody = document.getElementById("laufzettel-body");
    if (allEntries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty">No Laufzettel entries found.</td></tr>';
        return;
    }
    tbody.innerHTML = allEntries
        .map((lz) => {
            const nodes = (lz.nodes || [])
                .map((n) => `<span class="node-chip">${esc(n)}</span>`)
                .join("");
            const matCount = (lz.material || []).length;
            const matBadge = `<span class="material-count ${matCount === 0 ? "zero" : ""}">${matCount}</span>`;
            return `
        <tr>
            <td>${esc(lz.date || "-")}</td>
            <td>${esc(lz.owner_name || "-")}</td>
            <td>${esc(lz.member_id || "-")}</td>
            <td><code class="uid">${esc(lz.uid)}</code></td>
            <td>${formatTime(lz.start)}</td>
            <td><div class="nodes-list">${nodes || '<span style="color:var(--text-secondary)">-</span>'}</div></td>
            <td>${matBadge}</td>
            <td>${paymentBadge(lz)}</td>
            <td class="actions">
                <a href="/laufzettel/${lz.id}" class="btn btn-sm btn-secondary">View</a>
            </td>
        </tr>`;
        })
        .join("");
}

function paymentBadge(lz) {
    if (!lz.payment_method) return '<span class="pay-badge pay-none">–</span>';
    const labels = { bar: 'Bar', paypal: 'PayPal', karte: 'Karte' };
    const label = labels[lz.payment_method] || lz.payment_method;
    return `<span class="pay-badge pay-${esc(lz.payment_method)}">${label}</span>`;
}

function esc(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function formatTime(iso) {
    if (!iso) return "-";
    const d = new Date(iso);
    return d.toLocaleTimeString();
}

// ---- Modal helpers ----
function openNewLzModal() {
    document.getElementById("new-lz-form").reset();
    document.getElementById("new-lz-tag-hint").textContent = "";
    const now = new Date();
    document.getElementById("new-lz-date").value = now.toISOString().slice(0, 10);
    // Prefill datetime-local with current time (format: YYYY-MM-DDTHH:MM)
    const localIso = now.getFullYear() + '-' +
        String(now.getMonth() + 1).padStart(2, '0') + '-' +
        String(now.getDate()).padStart(2, '0') + 'T' +
        String(now.getHours()).padStart(2, '0') + ':' +
        String(now.getMinutes()).padStart(2, '0');
    document.getElementById("new-lz-start").value = localIso;
    document.getElementById("new-lz-member-select").value = "";
    document.getElementById("new-lz-modal").classList.remove("hidden");
    // Defer focus so Safari has time to make the element interactable
    setTimeout(function() {
        try { document.getElementById("new-lz-uid").focus(); } catch(e) {}
    }, 50);
}

function closeNewLzModal() {
    document.getElementById("new-lz-modal").classList.add("hidden");
}

// Auto-fill owner/member_id when a known UID is entered
document.getElementById("new-lz-uid").addEventListener("input", () => {
    const uid = document.getElementById("new-lz-uid").value.trim().toUpperCase();
    const tag = allTags.find((t) => t.uid === uid);
    const hint = document.getElementById("new-lz-tag-hint");
    if (tag) {
        document.getElementById("new-lz-owner").value = tag.owner_name || "";
        document.getElementById("new-lz-member-id").value = tag.member_id || "";
        hint.textContent = `✓ Bekannter Tag: ${tag.owner_name}`;
        hint.style.color = "var(--success)";
    } else if (uid.length > 0) {
        hint.textContent = "Unbekannter Tag — Name und Member ID bitte manuell eingeben.";
        hint.style.color = "var(--warning)";
    } else {
        hint.textContent = "";
    }
});

document.getElementById("new-lz-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
        uid: document.getElementById("new-lz-uid").value.trim().toUpperCase(),
        date: document.getElementById("new-lz-date").value || null,
        owner_name: document.getElementById("new-lz-owner").value.trim() || null,
        member_id: document.getElementById("new-lz-member-id").value.trim() || null,
    };
    const startVal = document.getElementById("new-lz-start").value;
    if (startVal) body.start = new Date(startVal).toISOString();

    const res = await fetch("/api/laufzettel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (res.ok) {
        const created = await res.json();
        closeNewLzModal();
        await loadLaufzettel();
        window.location.href = `/laufzettel/${created.id}`;
    } else {
        const err = await res.json();
        alert("Fehler: " + (err.detail || "Konnte Laufzettel nicht erstellen"));
    }
});

document.getElementById("new-laufzettel-btn").addEventListener("click", openNewLzModal);
document.getElementById("new-lz-close").addEventListener("click", closeNewLzModal);
document.getElementById("new-lz-cancel").addEventListener("click", closeNewLzModal);
document.getElementById("new-lz-overlay").addEventListener("click", closeNewLzModal);

// ---- Filter/refresh ----
document.getElementById("refresh-btn").addEventListener("click", loadLaufzettel);
document.getElementById("filter-btn").addEventListener("click", loadLaufzettel);
document.getElementById("clear-btn").addEventListener("click", () => {
    document.getElementById("filter-name").value = "";
    document.getElementById("filter-date").value = "";
    loadLaufzettel();
});
document.getElementById("filter-name").addEventListener("keydown", (e) => {
    if (e.key === "Enter") loadLaufzettel();
});

document.getElementById("new-lz-member-select").addEventListener("change", () => {
    const sel = document.getElementById("new-lz-member-select");
    const id = parseInt(sel.value);
    if (!id) return;
    const m = allMitglieder.find((x) => x.id === id);
    if (!m) return;
    document.getElementById("new-lz-owner").value = m.name;
    document.getElementById("new-lz-member-id").value = m.member_id;
});

loadMitglieder();
loadTags();
loadLaufzettel();

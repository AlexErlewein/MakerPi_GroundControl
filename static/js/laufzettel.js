let allEntries = [];
let allTags = [];

// ---- New-Laufzettel modal state ----
let currentMode = "member"; // "member" | "guest"
let selectedMember = null; // { id, member_id, name, nfc_uid, ... }
let guestNfcUid = null; // scanned guest tag uid (string|null)

function debounce(fn, wait) {
  let t;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), wait);
  };
}

async function loadTags() {
  try {
    const res = await fetch("/api/tags");
    allTags = await res.json();
    const dl = document.getElementById("uid-suggestions");
    dl.innerHTML = allTags
      .map(function (t) {
        return (
          '<option value="' +
          t.uid +
          '">' +
          (t.owner_name || "") +
          (t.member_id ? " (" + t.member_id + ")" : "") +
          "</option>"
        );
      })
      .join("");
  } catch (e) {
    console.warn("loadTags failed", e);
  }
}

let mode = "normal"; // "normal" | "history" | "only_open"

async function loadLaufzettel() {
  try {
    const uid = document.getElementById("filter-name").value.trim();
    const date = document.getElementById("filter-date").value;

    let url = "/api/laufzettel";
    const params = new URLSearchParams();
    if (date) params.set("date", date);
    if (mode === "history") {
      params.set("include_deleted", "1");
    } else if (mode === "only_open") {
      params.set("only_open", "1");
    }
    if (params.toString()) url += "?" + params.toString();

    const res = await fetch(url);
    allEntries = await res.json();

    if (uid) {
      const q = uid.toLowerCase();
      allEntries = allEntries.filter(
        (e) =>
          (e.owner_name || "").toLowerCase().includes(q) ||
          (e.uid || "").toLowerCase().includes(q) ||
          (e.member_id || "").toLowerCase().includes(q),
      );
    }

    renderStats();
    renderTable();
  } catch (e) {
    console.warn("loadLaufzettel failed", e);
  }
}

function renderStats() {
  document.getElementById("total-count").textContent = allEntries.length;

  const today = new Date().toISOString().slice(0, 10);
  const todayCount = allEntries.filter((e) => e.date === today).length;
  document.getElementById("today-count").textContent = todayCount;

  const unique = new Set(allEntries.map((e) => e.uid)).size;
  document.getElementById("cardholder-count").textContent = unique;

  const open = allEntries.filter((e) => !e.payment_method).length;
  document.getElementById("open-count").textContent = open;

  const paid = allEntries.filter((e) => e.payment_method).length;
  document.getElementById("paid-count").textContent = paid;
}

function renderTable() {
  const tbody = document.getElementById("laufzettel-body");
  if (allEntries.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="9" class="empty">No Laufzettel entries found.</td></tr>';
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
        <tr style="vertical-align:middle;">
            <td>${lz.id}</td>
            <td>${esc(lz.date || "-")}</td>
            <td>${esc(lz.owner_name || "-")}</td>
            <td>${esc(lz.member_id || "-")}</td>
            <td><code class="uid">${esc(lz.uid)}</code></td>
            <td>${formatTime(lz.start)}</td>
            <td><div class="nodes-list">${nodes || '<span style="color:var(--text-secondary)">-</span>'}</div></td>
            <td>${matBadge}</td>
            <td>${paymentBadge(lz)}</td>
            <td class="actions" style="text-align:center;">
                <a href="/laufzettel/${lz.id}" class="btn btn-sm btn-secondary">View</a>
            </td>
        </tr>`;
    })
    .join("");
}

function paymentBadge(lz) {
  if (lz.deleted_at)
    return '<span class="pay-badge pay-deleted">Gelöscht</span>';
  if (!lz.payment_method)
    return '<span class="pay-badge pay-open">Offen</span>';
  const labels = {
    bar: "Bar",
    paypal: "PayPal",
    karte: "Karte",
    wero: "Wero",
    closed: "Übertragen",
  };
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

// ---- Local date/time helpers (avoid UTC off-by-one) ----
function localDateStr(d) {
  return (
    d.getFullYear() +
    "-" +
    String(d.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(d.getDate()).padStart(2, "0")
  );
}
function localTimeStr(d) {
  return (
    String(d.getHours()).padStart(2, "0") +
    ":" +
    String(d.getMinutes()).padStart(2, "0")
  );
}

// ---- Modal helpers ----
function openNewLzModal() {
  document.getElementById("new-lz-form").reset();
  document.getElementById("new-lz-tag-hint").textContent = "";
  const now = new Date();
  document.getElementById("new-lz-date").value = localDateStr(now);
  document.getElementById("new-lz-start").value = localTimeStr(now);
  // Reset mode + state
  selectedMember = null;
  guestNfcUid = null;
  setMemberMode();
  clearSearchResults();
  updateGuestNfcDisplay();
  document.getElementById("new-lz-modal").classList.remove("hidden");
  // Defer focus so Safari has time to make the element interactable
  setTimeout(function () {
    try {
      document.getElementById("new-lz-owner").focus();
    } catch (e) {}
  }, 50);
}

function closeNewLzModal() {
  document.getElementById("new-lz-modal").classList.add("hidden");
  if (nfcScanSource) {
    nfcScanSource.close();
    nfcScanSource = null;
  }
}

// ---- Mode switching (member vs guest) ----
function setMemberMode() {
  currentMode = "member";
  document.getElementById("new-lz-guest-fields").classList.add("hidden");
  const badge = document.getElementById("new-lz-mode-badge");
  badge.style.display = "inline-block";
  badge.textContent = "Mitglied";
  badge.style.background = "var(--success)";
  badge.style.color = "#fff";
  document.getElementById("new-lz-switch-guest").style.display = "";
}

function setGuestMode() {
  currentMode = "guest";
  selectedMember = null;
  document.getElementById("new-lz-guest-fields").classList.remove("hidden");
  const badge = document.getElementById("new-lz-mode-badge");
  badge.style.display = "inline-block";
  badge.textContent = "Gast";
  badge.style.background = "var(--warning)";
  badge.style.color = "#fff";
  document.getElementById("new-lz-switch-guest").style.display = "none";
  clearSearchResults();
  document.getElementById("new-lz-guest-hint").style.display = "none";
}

// ---- Live member search ----
const doSearch = debounce(async (term) => {
  const box = document.getElementById("new-lz-search-results");
  if (currentMode === "guest") return;
  if (!term || term.length < 2) {
    clearSearchResults();
    return;
  }
  try {
    const res = await fetch(
      "/api/mitglieder?status=active&search=" + encodeURIComponent(term),
    );
    const list = await res.json();
    renderSearchResults(list);
  } catch (e) {
    console.warn("member search failed", e);
    clearSearchResults();
  }
}, 300);

function renderSearchResults(list) {
  const box = document.getElementById("new-lz-search-results");
  const hint = document.getElementById("new-lz-guest-hint");
  if (!list || list.length === 0) {
    clearSearchResults();
    if (currentMode === "member") hint.style.display = "";
    return;
  }
  hint.style.display = "none";
  box.innerHTML = list
    .slice(0, 8)
    .map(
      (m) =>
        '<div class="lz-search-item" data-mid="' +
        m.id +
        '">' +
        '<span class="lz-search-name">' +
        esc(m.name) +
        "</span>" +
        '<span class="lz-search-meta">' +
        (m.member_id ? esc(m.member_id) : "") +
        (m.email ? " · " + esc(m.email) : "") +
        "</span></div>",
    )
    .join("");
  box.classList.remove("hidden");
  Array.from(box.querySelectorAll(".lz-search-item")).forEach((el) => {
    el.addEventListener("click", () => {
      const mid = parseInt(el.getAttribute("data-mid"));
      const m = list.find((x) => x.id === mid);
      if (m) selectMember(m);
    });
  });
}

function clearSearchResults() {
  const box = document.getElementById("new-lz-search-results");
  box.innerHTML = "";
  box.classList.add("hidden");
}

function selectMember(m) {
  selectedMember = m;
  setMemberMode();
  document.getElementById("new-lz-owner").value = m.name;
  document.getElementById("new-lz-uid").value = m.nfc_uid || "";
  const hint = document.getElementById("new-lz-tag-hint");
  if (m.nfc_uid) {
    hint.textContent = "✓ NFC-UID aus Mitgliedskarte: " + m.nfc_uid;
    hint.style.color = "var(--success)";
  } else {
    hint.textContent = "Keine Karte hinterlegt — bitte Tag scannen/eingeben.";
    hint.style.color = "var(--warning)";
  }
  clearSearchResults();
  document.getElementById("new-lz-guest-hint").style.display = "none";
}

// ---- NFC scan helper (SSE) ----
let nfcScanSource = null;
function scanNfc(onCaptured, onStatus) {
  if (nfcScanSource) {
    nfcScanSource.close();
    nfcScanSource = null;
  }
  const url = "/api/scans/stream";
  const src = new EventSource(url);
  nfcScanSource = src;
  if (onStatus) onStatus("Warte auf Scan …");
  src.addEventListener("scan", (e) => {
    const data = JSON.parse(e.data);
    src.close();
    nfcScanSource = null;
    const uid = (data.uid || "").toUpperCase();
    if (uid && onCaptured) onCaptured(uid);
  });
  src.addEventListener("timeout", () => {
    src.close();
    nfcScanSource = null;
    if (onStatus) onStatus("Timeout – kein Scan empfangen.");
  });
  src.onerror = () => {
    src.close();
    nfcScanSource = null;
    if (onStatus) onStatus("Verbindungsfehler beim Scan.");
  };
}

// ---- Guest NFC tag capture ----
function updateGuestNfcDisplay() {
  const status = document.getElementById("new-lz-guest-nfc-status");
  const removeBtn = document.getElementById("new-lz-guest-nfc-remove");
  if (guestNfcUid) {
    status.innerHTML =
      '<code class="uid">' +
      esc(guestNfcUid) +
      '</code> <span style="color:var(--success);">✅</span>';
    removeBtn.classList.remove("hidden");
  } else {
    status.innerHTML =
      '<span style="color:var(--text-secondary);">Nicht verknüpft</span>';
    removeBtn.classList.add("hidden");
  }
}

// ---- Event wiring for the new modal ----
document.getElementById("new-lz-owner").addEventListener("input", () => {
  // Editing the name after a selection invalidates the selection
  if (selectedMember) {
    const cur = document.getElementById("new-lz-owner").value.trim();
    if (cur !== selectedMember.name) {
      selectedMember = null;
      if (currentMode === "member") doSearch(cur);
    }
    return;
  }
  if (currentMode === "member") {
    doSearch(document.getElementById("new-lz-owner").value.trim());
  }
});

document.getElementById("new-lz-switch-guest").addEventListener("click", (e) => {
  e.preventDefault();
  setGuestMode();
});
document.getElementById("new-lz-force-guest").addEventListener("click", (e) => {
  e.preventDefault();
  setGuestMode();
});

document.getElementById("new-lz-uid-scan").addEventListener("click", () => {
  const btn = document.getElementById("new-lz-uid-scan");
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = "📡 Warte …";
  scanNfc(
    (uid) => {
      document.getElementById("new-lz-uid").value = uid;
      btn.disabled = false;
      btn.textContent = orig;
      // Trigger the existing uid hint logic
      document.getElementById("new-lz-uid").dispatchEvent(new Event("input"));
    },
    (status) => {
      btn.disabled = false;
      btn.textContent = orig;
      const hint = document.getElementById("new-lz-tag-hint");
      hint.textContent = status;
      hint.style.color = "var(--warning)";
    },
  );
});

// Auto-fill owner hint when a known UID is entered manually
document.getElementById("new-lz-uid").addEventListener("input", () => {
  const uid = document.getElementById("new-lz-uid").value.trim().toUpperCase();
  const tag = allTags.find((t) => t.uid === uid);
  const hint = document.getElementById("new-lz-tag-hint");
  if (tag) {
    hint.textContent = "✓ Bekannter Tag: " + (tag.owner_name || "");
    hint.style.color = "var(--success)";
  } else if (uid.length > 0) {
    hint.textContent = "Unbekannter Tag.";
    hint.style.color = "var(--warning)";
  } else {
    hint.textContent = "";
  }
});

document.getElementById("new-lz-guest-nfc-scan").addEventListener("click", () => {
  const btn = document.getElementById("new-lz-guest-nfc-scan");
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = "📡 Warte …";
  scanNfc(
    (uid) => {
      guestNfcUid = uid;
      updateGuestNfcDisplay();
      btn.disabled = false;
      btn.textContent = orig;
    },
    (status) => {
      btn.disabled = false;
      btn.textContent = orig;
      const el = document.getElementById("new-lz-guest-nfc-status");
      el.innerHTML = '<span style="color:var(--warning);">' + esc(status) + "</span>";
    },
  );
});
document.getElementById("new-lz-guest-nfc-remove").addEventListener("click", () => {
  guestNfcUid = null;
  updateGuestNfcDisplay();
});

document.getElementById("new-lz-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const dateVal = document.getElementById("new-lz-date").value || null;
  const owner = document.getElementById("new-lz-owner").value.trim();
  const timeVal = document.getElementById("new-lz-start").value;
  let startIso = null;
  if (dateVal && timeVal) {
    startIso = new Date(dateVal + "T" + timeVal).toISOString();
  } else if (timeVal) {
    startIso = new Date(localDateStr(new Date()) + "T" + timeVal).toISOString();
  }

  let body;
  if (currentMode === "guest") {
    if (!owner) {
      alert("Bitte einen Namen eingeben.");
      return;
    }
    const address = document
      .getElementById("new-lz-guest-address")
      .value.trim();
    if (!address) {
      alert("Bitte eine Adresse eingeben.");
      return;
    }
    body = {
      is_guest: true,
      owner_name: owner,
      guest_address: address,
      guest_email: document.getElementById("new-lz-guest-email").value.trim() || null,
      guest_nfc_uid: guestNfcUid || null,
      date: dateVal,
      start: startIso,
    };
  } else {
    const uid = document.getElementById("new-lz-uid").value.trim().toUpperCase();
    if (!uid) {
      alert("Bitte eine Tag UID eingeben oder scannen.");
      return;
    }
    body = {
      uid: uid,
      date: dateVal,
      owner_name: owner || null,
      member_id: selectedMember ? selectedMember.member_id || null : null,
      mitglied_db_id: selectedMember ? selectedMember.id : null,
      start: startIso,
    };
  }

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

document
  .getElementById("new-laufzettel-btn")
  .addEventListener("click", openNewLzModal);
document
  .getElementById("new-lz-close")
  .addEventListener("click", closeNewLzModal);
document
  .getElementById("new-lz-cancel")
  .addEventListener("click", closeNewLzModal);
document
  .getElementById("new-lz-overlay")
  .addEventListener("click", closeNewLzModal);

// ---- Filter/refresh ----
document.getElementById("filter-btn").addEventListener("click", loadLaufzettel);
document.getElementById("clear-btn").addEventListener("click", () => {
  document.getElementById("filter-name").value = "";
  document.getElementById("filter-date").value = "";
  loadLaufzettel();
});
document.getElementById("filter-name").addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadLaufzettel();
});

// ---- History / only-open toggle ----
document.getElementById("history-btn").addEventListener("click", () => {
  if (mode === "history") {
    mode = "normal";
    document.getElementById("history-btn").classList.remove("btn-primary");
    document.getElementById("history-btn").classList.add("btn-secondary");
    document.getElementById("only-open-toggle").checked = false;
  } else {
    mode = "history";
    document.getElementById("history-btn").classList.remove("btn-secondary");
    document.getElementById("history-btn").classList.add("btn-primary");
    document.getElementById("only-open-toggle").checked = false;
  }
  loadLaufzettel();
});

document.getElementById("only-open-toggle").addEventListener("change", () => {
  if (document.getElementById("only-open-toggle").checked) {
    mode = "only_open";
    document.getElementById("history-btn").classList.remove("btn-primary");
    document.getElementById("history-btn").classList.add("btn-secondary");
  } else {
    mode = "normal";
  }
  loadLaufzettel();
});

loadTags();
loadLaufzettel();

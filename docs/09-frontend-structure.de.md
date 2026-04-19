# Frontend-Struktur

Die Web-UI ist eine Server-seitig gerenderte Jinja2-Anwendung mit JavaScript-Enhancement.

## Architektur

```
Server               Browser
   │                    │
   ├─ Jinja2 Template ─→├─ HTML Shell
   ├─ Static CSS ───────→├─ Styling
   ├─ Static JS ────────→├─ Interactivity
   │                    │
   └← API Calls (JSON) ─┘
```

Kein SPA-Framework (React, Vue, etc.) – bewusst einfach gehalten.

## Template-Struktur

```html
<!-- Jede Seite erweitert das Basis-Layout -->
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/page-specific.css">
</head>
<body>
    <header>...</header>
    <main id="app">
        <!-- Seiten-spezifischer Inhalt -->
    </main>
    <script src="/static/js/page-specific.js"></script>
</body>
</html>
```

## Seiten-Übersicht

| Seite | Template | JS-Datei | CSS-Datei |
|-------|----------|----------|-----------|
| **Dashboard** | `index.html` | Inline/keins | `style.css` |
| **Login** | `login.html` | Inline | `style.css` |
| **Tags** | `tags.html` | `tags.js` | `tags.css` |
| **Laufzettel** | `laufzettel.html` | `laufzettel.js` | `laufzettel.css` |
| **Laufzettel-Detail** | `laufzettel-detail.html` | `laufzettel-detail.js` | `laufzettel-detail.css` |
| **Katalog** | `katalog.html` | `katalog.js` | `katalog.css` |
| **Mitglieder** | `mitglieder.html` | `mitglieder.js` | — |
| **Admin** | `admin-users.html` | — | — |

## JavaScript-Muster

### Daten laden

```javascript
async function loadData() {
    try {
        const res = await fetch('/api/endpoint');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        renderData(data);
    } catch (e) {
        console.error('Laden fehlgeschlagen:', e);
        showError('Daten konnten nicht geladen werden');
    }
}
```

### Formular-Absendung

```javascript
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
        field: document.getElementById('field').value
    };
    
    const res = await fetch('/api/endpoint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    
    if (res.ok) {
        closeModal();
        loadData(); // Liste aktualisieren
    } else {
        const err = await res.json();
        alert('Fehler: ' + err.detail);
    }
});
```

### Rendering

```javascript
function renderItems(items) {
    const container = document.getElementById('list');
    container.innerHTML = items.map(item => `
        <div class="item" data-id="${item.id}">
            <span>${esc(item.name)}</span>
            <button onclick="deleteItem(${item.id})">Löschen</button>
        </div>
    `).join('');
}

// XSS-Schutz
function esc(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}
```

## CSS-Architektur

### Variablen (in `style.css`)

```css
:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --text-primary: #f0f6fc;
    --text-secondary: #8b949e;
    --accent: #58a6ff;
    --danger: #f85149;
    --success: #56d364;
    --warning: #e3b341;
}
```

### Utility-Klassen

```css
.hidden { display: none !important; }
.text-center { text-align: center; }
.mt-1 { margin-top: 0.5rem; }
.mb-2 { margin-bottom: 1rem; }
```

## Modal-Muster

```html
<!-- Modal-Struktur -->
<div id="modal" class="modal hidden">
    <div class="modal-overlay" onclick="closeModal()"></div>
    <div class="modal-box">
        <div class="modal-header">
            <h3>Titel</h3>
            <button onclick="closeModal()">✕</button>
        </div>
        <form id="modal-form">
            <!-- Formularfelder -->
        </form>
    </div>
</div>
```

```javascript
function openModal() {
    document.getElementById('modal').classList.remove('hidden');
    document.getElementById('modal-form').reset();
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
}

// ESC schließt Modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});
```

## Tabelle mit Aktionen

```html
<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Aktionen</th>
        </tr>
    </thead>
    <tbody id="table-body">
        <!-- Dynamisch gefüllt -->
    </tbody>
</table>
```

```javascript
function renderTable(items) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = items.map(item => `
        <tr>
            <td>${esc(item.name)}</td>
            <td><span class="badge ${item.status}">${item.status}</span></td>
            <td>
                <button class="btn btn-sm" onclick="editItem(${item.id})">Bearbeiten</button>
                <button class="btn btn-sm btn-danger" onclick="deleteItem(${item.id})">Löschen</button>
            </td>
        </tr>
    `).join('');
}
```

## Best Practices

### Tu's

- **Progressive Enhancement** – Seite funktioniert ohne JS, ist besser mit
- **Debounce** bei Sucheingaben (`setTimeout` + `clearTimeout`)
- **XSS-Escaping** bei allen dynamischen Inhalten
- **Fetch-Error-Handling** – immer `try/catch` + Nutzer-Feedback

### Nicht tu's

- Keine Frameworks ohne guten Grund
- Kein Client-seitiges Routing
- Keine komplexen Zustands-Management-Libs
- Kein Inline-Styling (außer für dynamische Positionen)

## Browser-Support

- Chrome/Edge (letzte 2 Versionen)
- Firefox (letzte 2 Versionen)
- Safari (letzte 2 Versionen)
- **Kein IE11** – bewusst nicht unterstützt

## Performance

- CSS/JS werden vom Browser gecacht
- Kein Build-Schritt nötig
- Lazy-Loading für große Tabellen (Pagination)

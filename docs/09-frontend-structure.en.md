# Frontend Structure

The frontend is server-rendered HTML with Jinja2 templates, enhanced by per-page JavaScript that calls the JSON API. There is no build step — files are served directly.

## Request lifecycle

```mermaid
sequenceDiagram
    participant B as Browser
    participant GC as FastAPI Backend
    participant DB as SQLite

    B->>GC: GET /laufzettel
    GC->>GC: Render laufzettel.html (Jinja2)
    GC-->>B: HTML page shell
    B->>B: Page JS runs (laufzettel.js)
    B->>GC: GET /api/laufzettel
    GC->>DB: SELECT ...
    DB-->>GC: rows
    GC-->>B: JSON response
    B->>B: Render table in DOM
```

## File structure

```
templates/              ← Jinja2 HTML shells
│
├── index.html          ← Dashboard (device list, MQTT live feed)
├── database.html       ← Message browser, DB stats
├── tags.html           ← RFID tag CRUD, scan events
├── laufzettel.html     ← Laufzettel list + new-entry modal
├── laufzettel-detail.html  ← Laufzettel editor + material modal
├── katalog.html        ← Material catalog tree editor
└── docs-layout.html    ← Docs site shell (sidebar, TOC, pager)

static/css/
├── style.css           ← Global CSS variables + shared styles
├── docs.css            ← Docs site layout + typography
├── laufzettel-detail.css   ← Material modal, mode toggle, price column
└── katalog.css         ← Catalog tree styles

static/js/
├── docs.js             ← Search, Mermaid init, scrollspy, sidebar toggle
├── laufzettel.js       ← List, filter, manual creation modal
├── laufzettel-detail.js    ← Dual-mode material modal, catalog selects, price calc
├── katalog.js          ← Location/Kategorie/Variante CRUD
└── (index, tags, etc.) ← Per-page JS
```

## Per-page JS pattern

Every page follows the same pattern:

```mermaid
flowchart TD
    LOAD["DOMContentLoaded"] --> FETCH["fetch /api/... (GET)"]
    FETCH --> RENDER["Render table / cards / list in DOM"]
    RENDER --> MODAL["User opens modal\n(edit or create)"]
    MODAL --> SUBMIT["Form submit → fetch POST/PUT/DELETE"]
    SUBMIT --> RELOAD["Re-fetch + re-render"]
```

### Example: add material entry

```javascript
// 1. Open modal, populate catalog dropdowns
async function openMaterialModal() {
    const locations = await fetch('/api/katalog/locations').then(r => r.json());
    renderLocationSelect(locations);
}

// 2. Cascade: on location change, load kategorien
locationSelect.addEventListener('change', async () => {
    const kategorien = await fetch(`/api/katalog/kategorien?location_id=${locationSelect.value}`)
        .then(r => r.json());
    renderKategorieSelect(kategorien);
});

// 3. Submit
async function saveMaterial() {
    await fetch(`/api/laufzettel/${id}/material`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(collectFormData()),
    });
    closeMaterialModal();
    loadMaterials();  // re-fetch + re-render
}
```

## Template page map

| Template | JS file | CSS file | API calls |
|---|---|---|---|
| `index.html` | `index.js` | `style.css` | `/api/status`, `/api/devices`, `/api/messages` |
| `database.html` | `database.js` | `style.css` | `/api/database/stats`, `/api/messages`, `/api/topics` |
| `tags.html` | `tags.js` | `style.css` | `/api/tags`, `/api/tags/scans` |
| `laufzettel.html` | `laufzettel.js` | `style.css` | `/api/laufzettel`, `/api/tags/{uid}` |
| `laufzettel-detail.html` | `laufzettel-detail.js` | `laufzettel-detail.css` | `/api/laufzettel/{id}`, `/api/katalog`, `/api/laufzettel/{id}/material` |
| `katalog.html` | `katalog.js` | `katalog.css` | `/api/katalog`, `/api/katalog/locations`, `/api/katalog/kategorien`, `/api/katalog/varianten` |
| `docs-layout.html` | `docs.js` | `docs.css` | `/api/search` (docs app) |

## Modals

Modals are built with plain HTML `<dialog>` or overlay divs — no external library. Each page manages its own modal state:

- `openModal()` — set display, populate fields
- `closeModal()` — hide, clear fields
- `submitModal()` — POST/PUT to API, then reload data

## Making UI changes

| Goal | Edit |
|---|---|
| Change page layout / HTML structure | `templates/<page>.html` |
| Change how data is fetched / rendered | `static/js/<page>.js` |
| Change table/modal/button styles | `static/css/<page>.css` |
| Add a new column to a table | HTML template + JS render function + API endpoint |
| Add a new field to a modal form | HTML template + JS form reader + API Pydantic model |

## CSS variables (from `style.css`)

| Variable | Value | Used for |
|---|---|---|
| `--bg-primary` | `#0d1117` | Page background |
| `--bg-secondary` | `#161b22` | Cards, sidebar |
| `--bg-tertiary` | `#21262d` | Table rows, inputs |
| `--border-color` | `#30363d` | All borders |
| `--text-primary` | `#f0f6fc` | Main text |
| `--text-secondary` | `#8b949e` | Muted text, labels |
| `--accent` | `#58a6ff` | Links, active items, highlights |
| `--success` | `#3fb950` | Status OK |
| `--warning` | `#d29922` | Warnings |
| `--danger` | `#f85149` | Errors, delete actions |

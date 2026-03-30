# Frontend Structure

The web frontend is server-rendered with Jinja templates and enhanced with per-page JavaScript.

## Templates

Templates live in:

- `templates/`

Current pages include:

- `index.html`
- `database.html`
- `device-detail.html`
- `tags.html`
- `laufzettel.html`
- `laufzettel-detail.html`
- `katalog.html`
- `docs-layout.html`

## JavaScript files

Scripts live in:

- `static/js/`

Pattern used in this project:

- one JS file per major page
- fetch API for JSON calls
- DOM rendering in plain JavaScript
- modal handling directly in page scripts

Examples:

- `tags.js` handles tag CRUD and scan rendering
- `laufzettel.js` handles listing, filtering, and manual creation modal
- `laufzettel-detail.js` handles detail editing and material management
- `katalog.js` handles location/category/variant CRUD

## CSS files

Styles live in:

- `static/css/`

Pattern used:

- `style.css` for global/shared styles
- per-page CSS for page-specific layout and components

## Data flow pattern

Most pages follow the same pattern:

1. template renders shell and placeholders
2. page JS loads JSON from `/api/...`
3. JS renders table/cards/forms
4. modal submit sends `POST`, `PUT`, or `DELETE`
5. page refreshes data via fetch

## Where to change UI behavior

### Change page layout

Edit the page template in `templates/`.

### Change API interactions

Edit the corresponding file in `static/js/`.

### Change page styling

Edit the matching CSS file in `static/css/`.

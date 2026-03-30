# System Architecture

This page gives the high-level technical structure of the project.

## Main components

```text
Workshop Device / Pico / Other Node
        ↓ MQTT publish
     Mosquitto Broker
        ↓ subscribe
    FastAPI Backend
      ↙         ↘
 SQLite DB      Web UI
```

## Runtime pieces

### MQTT broker

The backend expects a broker on:

- host: `localhost`
- port: `1883`

### Main FastAPI app

The main application lives in:

- `backend/main.py`

It handles:

- MQTT client startup
- DB access
- API endpoints
- HTML page routes
- page templates and static files

### Docs FastAPI app

The documentation site lives in:

- `backend/docs_app.py`

It handles:

- reading Markdown from `docs/`
- rendering docs pages
- sidebar navigation
- page table of contents

### SQLite database

The project uses:

- `groundcontrol.db`

The DB stores both operational data and workshop-domain data.

## Current code organization

### Backend

- `backend/main.py` — main application logic
- `backend/docs_app.py` — documentation site app

### Frontend templates

- `templates/*.html`

### Frontend JavaScript

- `static/js/*.js`

### Frontend styles

- `static/css/*.css`

### Documentation source

- `docs/*.md`

## Design note

The main app currently keeps a lot of responsibilities in one file. This is still workable for a small project, but it is a likely future refactor target.

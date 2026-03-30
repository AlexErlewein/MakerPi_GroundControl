# Quickstart

This page explains how to get GroundControl running locally and how to access both the main application and the documentation site.

## Start the main app

From the project root:

```bash
uv sync
uv run uvicorn backend.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

## Start the docs app

In a second terminal:

```bash
uv run uvicorn backend.docs_app:app --reload --port 8001
```

Open:

```text
http://localhost:8001
```

## Minimum working environment

The project expects:

- Python with `uv`
- SQLite via `groundcontrol.db`
- an MQTT broker, usually Mosquitto on `localhost:1883`

## First things to check

### 1. Main app opens

The dashboard should load on port `8000`.

### 2. Docs app opens

The docs home should redirect to the overview page on port `8001`.

### 3. MQTT is reachable

If MQTT is not available, the app may still start but device interactions and scan flows will not behave correctly.

### 4. Database file exists

The app will use `groundcontrol.db` in the project root.

## Common first tasks

- register a tag on `/tags`
- create a manual Laufzettel on `/laufzettel`
- add material in `/laufzettel/{id}`
- create catalog definitions on `/katalog`

## Local development routine

Use two terminals:

- **terminal 1**: main app on `8000`
- **terminal 2**: docs app on `8001`

This keeps the docs site independent while still living in the same repository.

## Raspberry Pi deployment note

The current project setup script only installs the main FastAPI service. The docs app should eventually get either:

- a second systemd service, or
- a reverse-proxy setup that exposes it separately

See [Operations and Deploy](./10-operations-and-deploy.md).

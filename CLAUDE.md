# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MakerPi GroundControl is a Raspberry Pi management system for a makerspace (H3cke). It provides MQTT broker monitoring, RFID member access control, a material catalog, work-order tracking ("Laufzettel"), and SumUp payment integration — all served via a FastAPI web app.

There are two separate FastAPI applications:
- **Main app** (`backend/main.py`) — dashboard, API, admin UI — port 8000
- **Docs app** (`backend/docs_app.py`) — Markdown documentation site — port 8001

## Commands

```bash
# Install dependencies (use uv, not pip)
uv sync

# Run main app locally (requires MQTT broker accessible)
uv run uvicorn backend.main:app --reload

# Run docs site locally
uv run uvicorn backend.docs_app:app --reload --port 8001

# Lint
uv run ruff check .
uv run ruff format --check .

# Run tests
uv run pytest

# Run a single test file
uv run pytest tests/test_foo.py -v

# Browse SQLite DBs (run on Pi or locally)
uv run sqlite_web -H 0.0.0.0 core.db

# Deploy to Pi (reads connection info from config/config.json)
./scripts/deploy.sh
./scripts/deploy.sh --update-deps

# Install auto-deploy timer on Pi (run once, as root, on the Pi itself)
sudo bash scripts/install-autodeploy.sh

# Trigger a manual auto-deploy run on Pi (without waiting for the timer)
sudo systemctl start groundcontrol-autodeploy.service

# Watch auto-deploy logs on Pi
sudo journalctl -u groundcontrol-autodeploy -f
```

## Configuration

Copy `config.json.example` to `config/config.json` (gitignored). The app reads this file at startup via `backend/config.py`, with env var fallbacks for every key. Key settings:

| Key | Purpose |
|---|---|
| `pi_host` / `pi_user` / `project_dir` | Used by `deploy.sh` only |
| `mqtt_broker` / `mqtt_port` | MQTT connection (default: `localhost:1883`) |
| `secret_key` | Session signing key — **change in production** |
| `admin_username` / `admin_password` | Seeded on first startup if no users exist |
| `sumup_*` | Payment credentials (see Payment section) |
| `easyverein_api_key` / `easyverein_org_id` | Member sync from easyVerein |

## Architecture

### Module Structure

The backend is split into domain modules, each owning its own SQLite database and SQLAlchemy `Base`. There are no ORM foreign keys across databases — cross-module lookups open a second `SessionLocal` inline.

```
backend/
├── main.py              # App factory: mounts all routers, starts APScheduler
├── config.py            # Single source for all config/env vars
├── docs_app.py          # Separate FastAPI app for the docs site
├── auth/                # DB: auth.db — Users, bcrypt passwords, sessions
├── core/                # DB: core.db — MQTTMessage, Device, TagScan; MQTT client
├── members/             # DB: members.db — Mitglied, RFIDTag, easyVerein sync
├── laufzettel/          # DB: laufzettel.db — Laufzettel, LaufzettelMaterial, payments
├── catalog/             # DB: catalog.db — Location, MaterialKategorie, MaterialVariante
└── member_routes.py     # Member self-service views (cross-module: reads auth+laufzettel+members+catalog)
```

Each module exposes:
- `models.py` — SQLAlchemy models + `to_dict()` methods
- `db.py` — `SessionLocal`, `get_db` dependency, `init_db()`
- `routes.py` — `APIRouter` with page routes and `/api/...` endpoints

### Router Mounting Order

In `main.py`, router order matters because `auth_router` and `core_router` both define `/`:
1. `auth_router` — `/login`, `/logout`, `/admin/users`, `/api/auth/*`
2. `member_router` — `/member/*`, `/api/member/*`, `/api/auth/login-rfid`
3. `core_router` — `/`, `/dashboard`, `/database`, `/api/status`, `/api/devices`, `/api/messages`, `/api/scans`
4. `members_router` — `/mitglieder`, `/tags`, `/api/mitglieder`, `/api/tags`
5. `laufzettel_router` — `/laufzettel`, `/api/laufzettel`, `/api/payment/*`
6. `catalog_router` — `/katalog`, `/api/katalog`

### Authentication Model

Two-level auth using Starlette `SessionMiddleware`:
- **Level 1 (any user):** `request.session["user"]` set → `check_auth()` passes. Members land on `/member`, admins on `/dashboard`.
- **Level 2 (admin actions):** `is_admin_verified()` checks `session["admin_verified"]` with a 10-minute inactivity timeout. Admin re-enters password via `POST /api/auth/verify-admin` to escalate.

Login accepts either admin users (from `auth.db`) or members with `login_username`/`login_password_hash` set in `members.db`. RFID tap login is handled separately via `POST /api/auth/login-rfid`.

### MQTT Data Flow

`backend/core/mqtt.py` connects to Mosquitto at startup and subscribes to `#` (all topics). Every message is persisted to `core.db`. For device-specific topics the handler also:
1. Upserts the `Device` record (auto-discovery)
2. On `{device_id}/scan` — validates the UID against `members.db` (RFIDTag), stores a `TagScan`, and auto-creates a `Laufzettel` entry in `laufzettel.db` for validated members

### Laufzettel Lifecycle

A Laufzettel (work order) is created automatically on a valid RFID scan, or manually via the admin UI. It accumulates `LaufzettelMaterial` entries. Once payment is recorded (`payment_method` set to `"bar"` or `"karte"`), the record is locked — all write endpoints return HTTP 409 until the payment is reset (admin only via `DELETE /api/laufzettel/{id}/pay`).

Payment modes are auto-selected from config:
- `sumup_mock: true` → mock (instant confirm)
- `sumup_reader_id` set → SumUp Solo Cloud API (card terminal)
- `sumup_affiliate_key` set, no reader → Payment Switch (`sumupmerchant://` deep-link)

### Material Catalog

Three-level hierarchy: `Location` → `MaterialKategorie` (with `pricing_model`) → `MaterialVariante` (with `price`). Pricing models: `per_unit`, `per_gram`, `per_volume_cm3`, `per_volume_l`, `per_minute`.

### EasyVerein Sync

`backend/members/easyverein.py` syncs members from the easyVerein API v2.0 into `members.db`. APScheduler runs this daily at 03:00. Admins can trigger it manually via `POST /api/mitglieder/sync`. The sync upserts by `member_id` (membershipNumber) and never overwrites `nfc_uid` or login credentials set locally.

### Docs Site

`backend/docs_app.py` renders `docs/*.md` files as HTML. Files named `*.de.md` are served by default; `*.en.md` versions are available via `?lang=en`. The sort order follows the numeric prefix (`00-`, `01-`, …). Mermaid diagrams in fenced code blocks are rendered via Mermaid.js.

## Key Conventions

- **UIDs are always uppercased** before storing or querying (`uid.upper()`).
- **Timestamps are UTC throughout.** `_utcnow()` helpers in each models file return `datetime.now(timezone.utc)`. The `_naive_to_utc()` helper patches naive datetimes from SQLite on read.
- **Cross-database queries** are done by importing the other module's `SessionLocal` and opening a new session inline — not via ORM relationships.
- **All models expose `to_dict()`** — API responses are built from this, not from Pydantic response models.
- The `nodes` field on `Laufzettel` is a **JSON-serialised list** of `device_id` strings stored as `Text`.

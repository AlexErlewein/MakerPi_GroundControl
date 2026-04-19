# Extension Guide

This page describes the current modular architecture and guidelines for extending it.

## Current architecture

The backend is now organized as a **modular monolith** — one FastAPI process with domain modules, each owning their own database:

```text
backend/
  main.py              # App factory, mounts all routers
  config.py            # Shared configuration
  docs_app.py          # Docs FastAPI app
  auth/                # Users, login, sessions
    models.py
    db.py
    routes.py
    dependencies.py
  members/             # Mitglieder + RFID tags
    models.py
    db.py
    routes.py
  laufzettel/          # Work orders + material tracking
    models.py
    db.py
    routes.py
  catalog/             # Material catalog
    models.py
    db.py
    routes.py
  core/                # MQTT, devices, scans
    models.py
    db.py
    mqtt.py
    routes.py
```

## Strengths of this design

- **Clear boundaries** — each domain owns its data and API
- **Independent databases** — modules can evolve schema without affecting others
- **Soft references** — cross-module links use string IDs, not FK constraints
- **Single deploy** — one process, no network overhead between modules

## Adding a new module

To add a new domain (e.g., `inventory`):

1. Create `backend/inventory/` with `__init__.py`, `models.py`, `db.py`, `routes.py`
2. Define your models inheriting from `declarative_base()`
3. Create engine using `sqlite:///./inventory.db`
4. Import and mount router in `backend/main.py`
5. Add auth check to your page routes using `backend.auth.dependencies.check_auth`

## Cross-module references

When Module A needs data from Module B:

- **Preferred**: Store a soft key (e.g., `member_id` as string) and fetch via API
- **Acceptable**: Import the other module's `SessionLocal` for read-only queries
- **Avoid**: Direct cross-module writes — keep transactions within one DB

## When to further split

Consider extracting a service if:

- A module needs independent scaling
- Different teams own different domains
- Deployment cadences diverge
- A module needs a different database type (Postgres, etc.)

## Documentation rule of thumb

Whenever you change one of these areas, update the docs in the same PR/change set:

- UI behavior
- MQTT topic contracts
- DB schema
- startup/deploy instructions
- material pricing rules

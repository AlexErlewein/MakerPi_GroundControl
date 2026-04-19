# System Architecture

This page describes the technical structure of the project — what runs where and how the pieces connect.

## Component overview

```mermaid
graph TB
    subgraph "Workshop Floor"
        D1["🖥 Pico W\n(NFC + MQTT)"]
        D2["🖥 Sensor Node\n(temp / humidity)"]
    end

    subgraph "Raspberry Pi (or local machine)"
        MB["Mosquitto\nBroker :1883"]
        GC["GroundControl\nFastAPI :8000\nModular routers"]
        DOCS["Docs App\nFastAPI :8001\nbackend/docs_app.py"]
        DB1[("SQLite\nauth.db")]
        DB2[("SQLite\nmembers.db")]
        DB3[("SQLite\nlaufzettel.db")]
        DB4[("SQLite\ncatalog.db")]
        DB5[("SQLite\ncore.db")]
        ZB["Zigbee2MQTT\n:8090 (optional)"]
    end

    subgraph "Browser"
        UI["Web UI\nJinja + JS"]
        DOCUI["Docs Site\nMarkdown rendered"]
    end

    D1 & D2 -->|MQTT publish| MB
    MB -->|paho-mqtt| GC
    GC <-->|SQLAlchemy ORM| DB1
    GC <-->|SQLAlchemy ORM| DB2
    GC <-->|SQLAlchemy ORM| DB3
    GC <-->|SQLAlchemy ORM| DB4
    GC <-->|SQLAlchemy ORM| DB5
    GC -->|HTML + JSON| UI
    DOCS -->|HTML rendered| DOCUI
    ZB -.->|optional MQTT| MB
```

## Runtime services

| Service | Port | Entry point | Description |
|---|---|---|---|
| GroundControl main app | 8000 | `backend/main.py` + modules | Core app: MQTT, DB, API, UI |
| Docs site | 8001 | `backend/docs_app.py` | Markdown docs renderer |
| Mosquitto MQTT broker | 1883 | system service | Message bus |
| Zigbee2MQTT (Pi only) | 8090 | system service | Zigbee bridge (optional) |
| sqlite-web (Pi only) | — | system service | DB browser (optional) |

## Code layout

```
MakerPi_GroundControl/
│
├── backend/
│   ├── main.py           ← App factory, mounts all routers
│   ├── config.py         ← Shared configuration
│   ├── docs_app.py       ← Docs FastAPI app (Markdown rendering)
│   ├── auth/             ← Auth module (users, login)
│   │   ├── models.py
│   │   ├── db.py
│   │   ├── routes.py
│   │   └── dependencies.py
│   ├── members/          ← Members module (mitglieder, tags)
│   │   ├── models.py
│   │   ├── db.py
│   │   └── routes.py
│   ├── laufzettel/       ← Laufzettel module (work orders)
│   │   ├── models.py
│   │   ├── db.py
│   │   └── routes.py
│   ├── catalog/          ← Catalog module (material catalog)
│   │   ├── models.py
│   │   ├── db.py
│   │   └── routes.py
│   └── core/             ← Core module (MQTT, devices, scans)
│       ├── models.py
│       ├── db.py
│       ├── mqtt.py
│       └── routes.py
│
├── templates/
│   ├── login.html        ← Public login / welcome page
│   ├── index.html        ← Dashboard (requires login)
│   ├── database.html     ← Message history
│   ├── tags.html         ← RFID tag admin
│   ├── laufzettel.html   ← Laufzettel list
│   ├── laufzettel-detail.html  ← Laufzettel editor + material modal
│   ├── katalog.html      ← Material catalog manager
│   ├── mitglieder.html   ← Member database
│   ├── admin-users.html  ← User management
│   └── docs-layout.html  ← Docs site shell template
│
├── static/
│   ├── css/
│   │   ├── style.css     ← Global variables + shared styles
│   │   ├── docs.css      ← Docs site styles
│   │   └── *.css         ← Per-page styles
│   └── js/
│       ├── docs.js       ← Docs search, Mermaid init, scrollspy
│       └── *.js          ← Per-page JS (fetch + DOM)
│
├── docs/
│   └── *.md              ← Documentation source files
│
├── scripts/
│   ├── setup.sh          ← Pi setup + systemd service installer
│   └── deploy.sh         ← Deployment helper
│
└── pyproject.toml        ← Python dependencies (uv)
```

## Startup sequence

```mermaid
sequenceDiagram
    participant UV as uvicorn
    participant APP as main.py
    participant DB as SQLite
    participant MQ as Mosquitto

    UV->>APP: import module
    APP->>DB1: create_all (auth.db)
    APP->>DB2: create_all (members.db)
    APP->>DB3: create_all (laufzettel.db)
    APP->>DB4: create_all (catalog.db)
    APP->>DB5: create_all (core.db)
    APP->>DB1: seed_admin_user() — create default user if none exist
    UV->>APP: lifespan startup
    APP->>MQ: paho-mqtt connect (localhost:1883)
    MQ-->>APP: on_connect callback
    APP->>MQ: subscribe "#" (all topics)
    Note over APP: App is ready
    UV->>APP: lifespan shutdown
    APP->>MQ: paho-mqtt disconnect
```

## Dependency chain

| Layer | Technology | Version |
|---|---|---|
| Python runtime | CPython | 3.12 |
| Package manager | uv | latest |
| Web framework | FastAPI | latest |
| ASGI server | uvicorn | latest |
| ORM | SQLAlchemy | latest |
| Database | SQLite | bundled |
| MQTT client | paho-mqtt | latest |
| Template engine | Jinja2 | latest |
| Docs rendering | markdown | 3.7 |
| Pydantic | pydantic | v2 |
| Password hashing | passlib + bcrypt | 1.7.4 / 3.x |
| Session signing | itsdangerous | 2.x |

## Design principles

> **Modular backend** — `backend/main.py` is now a lightweight app factory. Each domain (auth, members, laufzettel, catalog, core) has its own module with dedicated database, models, and routes. See [Extension Guide](./12-extension-guide.md).

> **Server-rendered UI** — Pages are Jinja2 templates. JavaScript enhances them but the HTML shell is always served from the backend. No separate SPA build step.

> **Session-based auth** — Login state is stored in a signed cookie via Starlette's `SessionMiddleware`. Only HTML page routes check for a session; `/api/` endpoints are left open (local network assumption). Users are stored in the `users` table in `auth.db` with bcrypt-hashed passwords.

> **SQLite only** — No Postgres, no connection pooling needed. One file, easy to back up and reset. `check_same_thread=False` allows use from the async MQTT handler thread.

# System-Architektur

Diese Seite beschreibt die technische Struktur des Projekts – was läuft wo und wie die Komponenten verbunden sind.

## Komponenten-Übersicht

```mermaid
graph TB
    subgraph "Werkstatt"
        D1["🖥 Pico W\n(NFC + MQTT)"]
        D2["🖥 Sensor Node\n(Temp / Feuchte)"]
    end

    subgraph "Raspberry Pi (oder lokale Maschine)"
        MB["Mosquitto\nBroker :1883"]
        GC["GroundControl\nFastAPI :8000\nModulare Router"]
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
        DOCUI["Docs Site\nMarkdown gerendert"]
    end

    D1 & D2 -->|MQTT publish| MB
    MB -->|paho-mqtt| GC
    GC <-->|SQLAlchemy ORM| DB1
    GC <-->|SQLAlchemy ORM| DB2
    GC <-->|SQLAlchemy ORM| DB3
    GC <-->|SQLAlchemy ORM| DB4
    GC <-->|SQLAlchemy ORM| DB5
    GC -->|HTML + JSON| UI
    DOCS -->|HTML gerendert| DOCUI
    ZB -.->|optional MQTT| MB
```

## Laufende Dienste

| Dienst | Port | Einstiegspunkt | Beschreibung |
|---|---|---|---|
| GroundControl Haupt-App | 8000 | `backend/main.py` + Module | Kern-App: MQTT, DB, API, UI |
| Docs Site | 8001 | `backend/docs_app.py` | Markdown-Docs-Renderer |
| Mosquitto MQTT Broker | 1883 | Systemdienst | Nachrichtenbus |
| Zigbee2MQTT (Pi only) | 8090 | Systemdienst | Zigbee-Bridge (optional) |
| sqlite-web (Pi only) | — | Systemdienst | DB-Browser (optional) |

## Code-Struktur

```
MakerPi_GroundControl/
│
├── backend/
│   ├── main.py           ← App-Factory, mounted alle Router
│   ├── config.py         ← Gemeinsame Konfiguration
│   ├── docs_app.py       ← Docs FastAPI-App
│   ├── auth/             ← Auth-Modul (Benutzer, Login)
│   │   ├── models.py
│   │   ├── db.py
│   │   ├── routes.py
│   │   └── dependencies.py
│   ├── members/          ← Members-Modul (Mitglieder, Tags, easyVerein-Sync)
│   │   ├── models.py
│   │   ├── db.py
│   │   ├── routes.py
│   │   ├── easyverein.py ← easyVerein-API-Sync
│   │   └── signature.py  ← HMAC-Karten-Signatur + Mifare-Sektor-Schlüsselableitung
│   ├── laufzettel/       ← Laufzettel-Modul (Aufträge)
│   │   ├── models.py
│   │   ├── db.py
│   │   ├── routes.py
│   │   └── pdf.py        ← PDF-Erzeugung + Google-Drive-Upload
│   ├── catalog/          ← Catalog-Modul (Materialkatalog)
│   │   ├── models.py
│   │   ├── db.py
│   │   └── routes.py
│   ├── core/             ← Core-Modul (MQTT, Geräte, Scans)
│   │   ├── models.py
│   │   ├── db.py
│   │   ├── mqtt.py
│   │   └── routes.py
│   ├── buchhaltung/      ← Buchhaltungs-Modul
│   │   ├── models.py
│   │   ├── db.py
│   │   ├── routes.py
│   │   └── accounting.py
│   ├── push/             ← Web-Push-Benachrichtigungen
│   │   └── routes.py
│   ├── shopify/          ← Shopify-Integration
│   │   └── routes.py
│   ├── plane/            ← Plane-Bugtracker-Integration (öffentliches Bug-Report-Formular)
│   │   └── routes.py
│   ├── email_utils.py    ← Async SMTP-E-Mail-Versand (aiosmtplib)
│   ├── email_templates.py ← HTML-E-Mail-Templates (Quittung, easyVerein-Anmeldung)
│   ├── gdrive.py         ← Google-Drive-OAuth + Upload-Helper
│   └── member_routes.py  ← Modulübergreifende Mitglied-Self-Service-Routen (auth+laufzettel+members+catalog)
│
├── templates/
│   ├── login.html        ← Öffentliche Login-/Willkommensseite
│   ├── index.html        ← Dashboard (erfordert Login)
│   ├── database.html     ← Nachrichtenhistorie
│   ├── tags.html         ← RFID-Tag-Admin
│   ├── laufzettel.html   ← Laufzettel-Liste
│   ├── laufzettel-detail.html  ← Laufzettel-Editor + Material-Modal
│   ├── katalog.html      ← Materialkatalog-Manager
│   ├── mitglieder.html              ← Mitgliedsdatenbank
│   ├── admin-users.html             ← Benutzerverwaltung
│   ├── member-laufzettel-open.html  ← Offene Laufzettel des Mitglieds
│   ├── member-laufzettel-historie.html ← Zahlungshistorie des Mitglieds
│   ├── member-laufzettel-detail.html   ← Mitglied-Laufzettel-Detail (nur Lesezugriff)
│   ├── member-konto.html              ← Mitglied-Kontoinfo
│   └── docs-layout.html  ← Docs-Site-Shell-Template
│
├── static/
│   ├── css/
│   │   ├── style.css     ← Globale Variablen + gemeinsame Styles
│   │   ├── docs.css      ← Docs-Site-Styles
│   │   └── *.css         ← Seiten-spezifische Styles
│   └── js/
│       ├── docs.js       ← Docs-Suche, Mermaid-Init, Scrollspy
│       └── *.js          ← Seiten-spezifisches JS (fetch + DOM)
│
├── docs/
│   └── *.md              ← Dokumentations-Quelldateien
│
├── scripts/
│   ├── setup.sh          ← Pi-Setup + systemd-Service-Installer
│   └── deploy.sh         ← Deployment-Helfer
│
└── pyproject.toml        ← Python-Abhängigkeiten (uv)
```

## Start-Sequenz

```mermaid
sequenceDiagram
    participant UV as uvicorn
    participant APP as main.py
    participant DB as SQLite
    participant MQ as Mosquitto

    UV->>APP: Modul importieren
    APP->>DB1: create_all (auth.db)
    APP->>DB2: create_all (members.db)
    APP->>DB3: create_all (laufzettel.db)
    APP->>DB4: create_all (catalog.db)
    APP->>DB5: create_all (core.db)
    APP->>DB1: seed_admin_user() – Standard-User erstellen falls keiner existiert
    UV->>APP: lifespan startup
    APP->>APP: APScheduler starten
    APP->>APP: easyVerein-Sync einplanen (täglich 03:00)
    APP->>MQ: paho-mqtt connect (localhost:1883)
    MQ-->>APP: on_connect callback
    APP->>MQ: subscribe "#" (alle Topics)
    Note over APP: App ist bereit
    UV->>APP: lifespan shutdown
    APP->>MQ: paho-mqtt disconnect
    APP->>APP: Scheduler herunterfahren
```

## Technologie-Stack

| Ebene | Technologie | Version |
|---|---|---|
| Python-Runtime | CPython | 3.12 |
| Paketmanager | uv | latest |
| Web-Framework | FastAPI | latest |
| ASGI-Server | uvicorn | latest |
| ORM | SQLAlchemy | latest |
| Datenbank | SQLite | bundled |
| MQTT-Client | paho-mqtt | latest |
| Job-Scheduler | APScheduler | latest |
| Template-Engine | Jinja2 | latest |
| Docs-Rendering | markdown | 3.7 |
| Pydantic | pydantic | v2 |
| Passwort-Hashing | passlib + bcrypt | 1.7.4 / 3.x |
| Session-Signierung | itsdangerous | 2.x |
| E-Mail (async SMTP) | aiosmtplib | latest |

## Design-Prinzipien

> **Modulares Backend** — `backend/main.py` ist jetzt eine leichtgewichtige App-Factory. Jede Domäne (auth, members, laufzettel, catalog, core) hat ihr eigenes Modul mit dedizierter Datenbank, Models und Routes. Siehe [Extension Guide](./12-extension-guide).

> **Server-seitig gerenderte UI** — Seiten sind Jinja2-Templates. JavaScript erweitert sie, aber die HTML-Shell wird immer vom Backend ausgeliefert. Kein separater SPA-Build-Schritt.

> **Session-basierte Auth** — Login-Status wird in einem signierten Cookie via Starlettes `SessionMiddleware` gespeichert. Nur HTML-Seiten-Routen prüfen auf eine Session; `/api/` Endpunkte bleiben offen (Annahme: lokales Netzwerk). Benutzer werden in der `users`-Tabelle in `auth.db` mit bcrypt-gehashten Passwörtern gespeichert.

> **Nur SQLite** — Kein Postgres, kein Connection-Pooling nötig. Eine Datei, einfach zu sichern und zurückzusetzen. `check_same_thread=False` erlaubt die Nutzung vom async MQTT-Handler-Thread.


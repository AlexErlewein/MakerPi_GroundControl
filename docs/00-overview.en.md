# GroundControl Overview

MakerPi GroundControl is the central web and database system for managing MQTT-connected workshop devices, RFID tags, Laufzettel (usage records), and material tracking.

## How the system fits together

```mermaid
graph LR
    subgraph Workshop
        D1["🖥 Pico W #1\n(NFC reader)"]
        D2["🖥 Pico W #2\n(Sensor node)"]
    end
    subgraph Server["Raspberry Pi / Server"]
        MB["Mosquitto\nBroker :1883"]
        GC["GroundControl\nFastAPI :8000"]
        DB["SQLite DBs\nauth/core/members/etc"]
        DOCS["Docs Site\nFastAPI :8001"]
    end
    subgraph Operator
        UI["🌐 Web Browser"]
    end
    D1 & D2 -->|"MQTT publish"| MB
    MB -->|"paho-mqtt subscribe"| GC
    GC <-->|"SQLAlchemy"| DB
    GC -->|"HTML/JSON"| UI
    DOCS -->|"Markdown"| UI
```

## Main user-facing concepts

### Devices

A device is a Pico W or any MQTT-speaking node that publishes status or sensor data. Devices are discovered automatically from MQTT topics and shown in the dashboard.

### RFID Tags

A registered NFC card, optionally linked to a Mitglied (member).

| Field | Description |
|---|---|
| `uid` | Hardware UID from the NFC card |
| `member_id` | Soft reference to `mitglieder.member_id` |
| `owner_name` | Human name of the card holder |
| `owner_email` | Email address |
| `active` | Whether scans are accepted |
| `is_admin` | If true, grants admin access via RFID login |
| `notes` | Free-text notes |

### Laufzettel

A **Laufzettel** is a day-specific usage record. One is created automatically the first time a known tag or Mitglied scans in on a given day. Non-members can also create a Laufzettel by scanning a QR code.

| Field | Description |
|---|---|
| `uid` | Tag UID (legacy link) |
| `date` | Usage date |
| `start` | First scan time |
| `owner_name` | Copied from tag at time of scan |
| `member_id` | Copied from tag at time of scan (legacy) |
| `mitglied_id` | FK to `mitglieder.id` — preferred link |
| `guest_id` | UUID for guest sessions (non-members) |
| `guest_email` | Optional email for guests |
| `nodes` | List of devices/stations visited |

### Material entries

Material is recorded on a Laufzettel in two modes:

| Mode | When to use |
|---|---|
| **Freitext** | Quick one-off entry, no catalog needed |
| **Aus Katalog** | Catalog-backed entry with automatic price calculation |

### Material catalog

```mermaid
graph TD
    L["📍 Location\ne.g. Töpferei"] --> K["🗂 Kategorie\ne.g. Ton"]
    K --> U1["📁 Unterkategorie: Rot\npricing: per_gram\nunit: g\ntax: 19%"]
    K --> U2["📁 Unterkategorie: Weiß\npricing: per_gram\nunit: g\ntax: 19%"]
    U1 --> V1["🔷 Variante: fein\n0.05 €/g"]
    U1 --> V2["🔷 Variante: grob\n0.03 €/g"]
    U2 --> V3["🔷 Variante: weiß-fein\n0.04 €/g"]
    L2["📍 Holz-Werkstatt"] --> K2["🗂 Holz"]
    K2 --> U3["📁 Unterkategorie: Hartholz\npricing: per_volume_cm3\nunit: cm³\ntax: 19%"]
    U3 --> V4["🔷 Eiche\n0.12 €/cm³"]
    U3 --> V5["🔷 Esche\n0.09 €/cm³"]
```

## Typical operator workflow

```mermaid
flowchart LR
    A["Open Dashboard\n/ "] --> B["Check devices\nare online"]
    B --> C["Register tags\n/tags"]
    C --> D["Tag used in\nworkshop"]
    D -->|"automatic"| E["Laufzettel\ncreated"]
    D -->|"manual fallback"| E
    E --> F["Review & edit\n/laufzettel/id"]
    F --> G["Add material\n(Freitext or Katalog)"]
    G --> H["Done ✓"]
```

## Important pages

| URL | Purpose |
|---|---|
| `/` | Dashboard — device status, recent messages, system health |
| `/database` | Message history and DB statistics |
| `/tags` | RFID tag administration |
| `/laufzettel` | Laufzettel list and manual creation |
| `/laufzettel/{id}` | Laufzettel detail and material editing |
| `/katalog` | Material catalog management |
| `/guest/laufzettel` | Guest entry form for non-members (QR code) |

## Ports at a glance

| Service | Port | URL |
|---|---|---|
| Main app | 8000 | `http://localhost:8000` |
| Docs site | 8001 | `http://localhost:8001` |
| MQTT broker | 1883 | `localhost:1883` |
| Zigbee2MQTT (Pi only) | 8090 | `http://localhost:8090` |

## Where to go next

- [Quickstart](./01-quickstart.md) — get running in 2 minutes
- [Web UI Guide](./02-web-ui.md) — what each page does
- [Tags and Laufzettel](./03-tags-and-laufzettel.md) — core user workflow in detail
- [Guest Laufzettel](./17-guest-laufzettel.md) — non-member usage via QR code
- [Configuration Reference](./18-configuration-reference.md) — all config keys, where to get API keys

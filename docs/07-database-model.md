# Database Model

This page describes every table, its fields, and the relationships between them. Since the modular refactor, tables are distributed across **5 separate SQLite databases**.

## Database Overview

| Database | Module | Tables |
|---|---|---|
| `auth.db` | `backend/auth/` | `users` |
| `members.db` | `backend/members/` | `mitglieder`, `rfid_tags` |
| `laufzettel.db` | `backend/laufzettel/` | `laufzettel`, `laufzettel_material` |
| `catalog.db` | `backend/catalog/` | `locations`, `material_kategorie`, `material_variante` |
| `core.db` | `backend/core/` | `mqtt_messages`, `devices`, `tag_scans` |

Each module owns its database connection and models. Cross-database references use soft keys (e.g., `member_id` stored as string) rather than foreign keys.

## Entity-Relationship diagram

```mermaid
erDiagram
    RFIDTag {
        int id PK
        string uid UK
        string owner_name
        string member_id
        bool active
        string notes
        datetime created_at
    }
    Laufzettel {
        int id PK
        string uid
        date date
        string start
        string owner_name
        string member_id
        string nodes
        string payment_method
        datetime paid_at
        datetime created_at
    }
    LaufzettelMaterial {
        int id PK
        int laufzettel_id FK
        int variante_id FK
        string name
        float menge
        string unit
        float laenge_cm
        float breite_cm
        float hoehe_cm
        float calculated_price
        datetime created_at
    }
    Location {
        int id PK
        string name UK
    }
    MaterialKategorie {
        int id PK
        int location_id FK
        string name
        string preismodell
        string einheit
    }
    MaterialUnterkategorie {
        int id PK
        int kategorie_id FK
        string name
        string pricing_model
        string unit
        float tax_rate
        bool is_spende
    }
    MaterialVariante {
        int id PK
        int kategorie_id FK
        int unterkategorie_id FK
        string name
        float price
        string pricing_model
        string unit
        float tax_rate
        bool is_spende
    }
    MQTTMessage {
        int id PK
        string topic
        string payload
        datetime timestamp
        string device_id
    }
    Device {
        int id PK
        string device_id UK
        string last_seen
        string status
        string last_payload
    }
    TagScan {
        int id PK
        string uid
        string device_id
        datetime timestamp
        bool validated
    }

    RFIDTag ||--o{ Laufzettel : "uid (app-level)"
    Laufzettel ||--o{ LaufzettelMaterial : "laufzettel_id"
    Location ||--o{ MaterialKategorie : "location_id"
    MaterialKategorie ||--o{ MaterialUnterkategorie : "kategorie_id"
    MaterialUnterkategorie ||--o{ MaterialVariante : "unterkategorie_id"
    MaterialVariante ||--o{ LaufzettelMaterial : "variante_id (optional)"
```

## Table reference

### `mqtt_messages`

Raw store of every received MQTT message.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `topic` | TEXT | Full topic string |
| `payload` | TEXT | Raw payload string |
| `timestamp` | DATETIME | Server receive time (UTC) |
| `device_id` | TEXT | Extracted from topic prefix |

### `devices`

One row per discovered device, updated on every message.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `device_id` | TEXT UNIQUE | Topic prefix |
| `last_seen` | TEXT | ISO timestamp string |
| `status` | TEXT | Last known status string |
| `last_payload` | TEXT | Last message payload |

### `rfid_tags`

Registered cardholders.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `uid` | TEXT UNIQUE | NFC card UID |
| `owner_name` | TEXT | Display name |
| `member_id` | TEXT | Workshop member number |
| `active` | BOOLEAN | Default true |
| `notes` | TEXT | Free-text notes |
| `created_at` | DATETIME | Auto |

### `tag_scans`

Event log of every NFC scan received.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `uid` | TEXT | Scanned UID |
| `device_id` | TEXT | Source device |
| `timestamp` | DATETIME | Scan time |
| `validated` | BOOLEAN | True if UID matched a registered tag |

### `laufzettel`

One record per cardholder per day.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `uid` | TEXT | RFID UID |
| `date` | DATE | Usage date |
| `start` | TEXT | First scan time (HH:MM) |
| `owner_name` | TEXT | Copied from tag at creation |
| `member_id` | TEXT | Copied from tag at creation |
| `nodes` | TEXT | JSON list of device IDs |
| `payment_method` | TEXT | `bar` / `paypal` / `karte` — null until paid |
| `paid_at` | DATETIME | UTC timestamp of payment — null until paid |
| `created_at` | DATETIME | Auto |
| — | UNIQUE | `(uid, date)` |

### `laufzettel_material`

Material entries attached to a Laufzettel.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `laufzettel_id` | INTEGER FK | → `laufzettel.id` |
| `variante_id` | INTEGER FK | → `material_variante.id` (nullable) |
| `name` | TEXT | Material name |
| `menge` | FLOAT | Amount used |
| `unit` | TEXT | Unit string |
| `laenge_cm` | FLOAT | For volume pricing |
| `breite_cm` | FLOAT | For volume pricing |
| `hoehe_cm` | FLOAT | For volume pricing |
| `calculated_price` | FLOAT | Frozen at save time |
| `created_at` | DATETIME | Auto |

### `locations`

Top-level catalog grouping.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `name` | TEXT UNIQUE | Location name |

### `material_kategorie`

Category with pricing model and unit.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `location_id` | INTEGER FK | → `locations.id` |
| `name` | TEXT | Category name |
| `preismodell` | TEXT | `per_gram` / `per_volume_cm3` / `per_unit` |
| `einheit` | TEXT | Display unit |

### `material_variante`

Concrete priced variant.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `kategorie_id` | INTEGER FK | → `material_kategorie.id` |
| `name` | TEXT | Variant name |
| `preis_pro_einheit` | FLOAT | Price per unit (€) |

## Key relationships

```mermaid
flowchart LR
    T["rfid_tags\n(uid)"] -->|"app-level\nuid match"| L["laufzettel\n(uid, date)"]
    L --> LM["laufzettel_material"]
    MV["material_variante"] -->|"optional FK\nvariante_id"| LM
    MK["material_kategorie"] --> MV
    LOC["locations"] --> MK
```

> **No hard FK from laufzettel → rfid_tags.** The relation uses `uid` as a shared key managed at the application level. This allows Laufzettel entries to exist for unregistered UIDs (e.g. manual creation).

## Migration approach

Each module uses SQLAlchemy `create_all()` on startup to create its own tables. There is no automatic migration for schema changes — each module manages its own database independently.

If schema changes become frequent, adding **Alembic** per module is the recommended next step. See [Extension Guide](./12-extension-guide.md).

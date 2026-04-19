# Datenbank-Modell

Diese Seite beschreibt alle Tabellen, ihre Felder und die Beziehungen zwischen ihnen. Seit dem modularen Refaktor sind die Tabellen über **5 separate SQLite-Datenbanken** verteilt.

## Datenbank-Übersicht

| Datenbank | Modul | Tabellen |
|---|---|---|
| `auth.db` | `backend/auth/` | `users` |
| `members.db` | `backend/members/` | `mitglieder`, `rfid_tags` |
| `laufzettel.db` | `backend/laufzettel/` | `laufzettel`, `laufzettel_material` |
| `catalog.db` | `backend/catalog/` | `locations`, `material_kategorie`, `material_variante` |
| `core.db` | `backend/core/` | `mqtt_messages`, `devices`, `tag_scans` |

Jedes Modul besitzt seine eigene Datenbankverbindung und Models. Datenbank-übergreifende Referenzen verwenden Soft-Keys (z.B. `member_id` als String) statt Fremdschlüsseln.

## Entity-Relationship-Diagramm

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
    MaterialVariante {
        int id PK
        int kategorie_id FK
        string name
        float preis_pro_einheit
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

    RFIDTag ||--o{ Laufzettel : "uid (App-Ebene)"
    Laufzettel ||--o{ LaufzettelMaterial : "laufzettel_id"
    Location ||--o{ MaterialKategorie : "location_id"
    MaterialKategorie ||--o{ MaterialVariante : "kategorie_id"
    MaterialVariante ||--o{ LaufzettelMaterial : "variante_id (optional)"
```

## Tabellen-Referenz

### `mqtt_messages`

Rohspeicher aller empfangenen MQTT-Nachrichten.

| Spalte | Typ | Hinweise |
|---|---|---|
| `id` | INTEGER PK | Auto-Inkrement |
| `topic` | TEXT | Vollständiger Topic-String |
| `payload` | TEXT | Roh-Payload-String |
| `timestamp` | DATETIME | Server-Empfangszeit (UTC) |
| `device_id` | TEXT | Aus Topic-Präfix extrahiert |

### `devices`

Eine Zeile pro erkanntem Gerät, aktualisiert bei jeder Nachricht.

| Spalte | Typ | Hinweise |
|---|---|---|
| `id` | INTEGER PK | Auto-Inkrement |
| `device_id` | TEXT UNIQUE | Topic-Präfix |
| `last_seen` | TEXT | ISO-Zeitstempel-String |
| `status` | TEXT | Letzter bekannter Status-String |
| `last_payload` | TEXT | Letzte Nachrichten-Payload |

### `rfid_tags`

Registrierte Karteninhaber.

| Spalte | Typ | Hinweise |
|---|---|---|
| `id` | INTEGER PK | Auto-Inkrement |
| `uid` | TEXT UNIQUE | NFC-Karten-UID |
| `owner_name` | TEXT | Anzeigename |
| `member_id` | TEXT | Workshop-Mitgliedsnummer |
| `active` | BOOLEAN | Standard true |
| `notes` | TEXT | Freitext-Notizen |
| `created_at` | DATETIME | Auto |

### `tag_scans`

Ereignis-Log aller empfangenen NFC-Scans.

| Spalte | Typ | Hinweise |
|---|---|---|
| `id` | INTEGER PK | Auto-Inkrement |
| `uid` | TEXT | Gescannte UID |
| `device_id` | TEXT | Quellgerät |
| `timestamp` | DATETIME | Scan-Zeit |
| `validated` | BOOLEAN | True wenn UID einem registrierten Tag entsprach |

### `laufzettel`

Ein Datensatz pro Karteninhaber pro Tag.

| Spalte | Typ | Hinweise |
|---|---|---|
| `id` | INTEGER PK | Auto-Inkrement |
| `uid` | TEXT | RFID-UID |
| `date` | DATE | Nutzungsdatum |
| `start` | TEXT | Erste Scan-Zeit (HH:MM) |
| `owner_name` | TEXT | Beim Erstellen aus Tag kopiert |
| `member_id` | TEXT | Beim Erstellen aus Tag kopiert |
| `nodes` | TEXT | JSON-Liste der Geräte-IDs |
| `payment_method` | TEXT | `bar` / `karte` — null bis zur Zahlung |
| `paid_at` | DATETIME | UTC-Zeitstempel der Zahlung — null bis zur Zahlung |
| `created_at` | DATETIME | Auto |
| — | UNIQUE | `(uid, date)` |

### `laufzettel_material`

Mit einem Laufzettel verbundene Material-Einträge.

| Spalte | Typ | Hinweise |
|---|---|---|
| `id` | INTEGER PK | Auto-Inkrement |
| `laufzettel_id` | INTEGER FK | → `laufzettel.id` |
| `variante_id` | INTEGER FK | → `material_variante.id` (nullable) |
| `name` | TEXT | Materialname |
| `menge` | FLOAT | Verwendete Menge |
| `unit` | TEXT | Einheits-String |
| `laenge_cm` | FLOAT | Für Volumenpreise |
| `breite_cm` | FLOAT | Für Volumenpreise |
| `hoehe_cm` | FLOAT | Für Volumenpreise |
| `calculated_price` | FLOAT | Eingefroren beim Speichern |
| `created_at` | DATETIME | Auto |

### `locations`

Top-Level Katalog-Gruppierung.

| Spalte | Typ | Hinweise |
|---|---|---|
| `id` | INTEGER PK | Auto-Inkrement |
| `name` | TEXT UNIQUE | Standortname |

### `material_kategorie`

Kategorie mit Preismodell und Einheit.

| Spalte | Typ | Hinweise |
|---|---|---|
| `id` | INTEGER PK | Auto-Inkrement |
| `location_id` | INTEGER FK | → `locations.id` |
| `name` | TEXT | Kategoriename |
| `preismodell` | TEXT | `pro_gramm` / `pro_volumen_cm3` / `pro_stueck` |
| `einheit` | TEXT | Anzeigeeinheit |

### `material_variante`

Konkrete, preisgekrönte Variante.

| Spalte | Typ | Hinweise |
|---|---|---|
| `id` | INTEGER PK | Auto-Inkrement |
| `kategorie_id` | INTEGER FK | → `material_kategorie.id` |
| `name` | TEXT | Variantenname |
| `preis_pro_einheit` | FLOAT | Preis pro Einheit (€) |

## Wichtige Beziehungen

```mermaid
flowchart LR
    T["rfid_tags\n(uid)"] -->|"App-Ebene\nuid-Match"| L["laufzettel\n(uid, date)"]
    L --> LM["laufzettel_material"]
    MV["material_variante"] -->|"optional FK\nvariante_id"| LM
    MK["material_kategorie"] --> MV
    LOC["locations"] --> MK
```

> **Kein harter FK von laufzettel → rfid_tags.** Die Beziehung nutzt `uid` als gemeinsamen Key auf App-Ebene. Das erlaubt Laufzettel-Einträge für unregistrierte UIDs (z.B. manuelle Erstellung).

## Migrations-Ansatz

Jedes Modul nutzt SQLAlchemy `create_all()` beim Start, um seine eigenen Tabellen zu erstellen. Es gibt keine automatische Migration für Schema-Änderungen — jedes Modul verwaltet seine Datenbank unabhängig.

Wenn Schema-Änderungen häufiger werden, ist **Alembic** pro Modul die empfohlene nächste Stufe. Siehe [Extension Guide](./12-extension-guide).

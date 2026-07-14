# Tags and Laufzettel

This page explains how RFID tags and Laufzettel work together — the core of the daily workshop workflow.

## Registered tags

A registered RFID tag lives in the `rfid_tags` table and represents a known cardholder.

| Field | Type | Description |
|---|---|---|
| `uid` | string | Hardware UID from the NFC card (e.g. `04AABBCCDD`) |
| `owner_name` | string | Human name of the cardholder |
| `member_id` | string | Workshop member number |
| `active` | boolean | If false, scans are logged but not acted on |
| `notes` | text | Free-text notes |
| `created_at` | datetime | When the tag was registered |

> **Note:** Tags are not created automatically. An operator must register a tag via the `/tags` page before it triggers Laufzettel creation.

## Automatic Laufzettel creation (NFC scan flow)

When a device sends an NFC payload via MQTT, the backend runs through this sequence:

```mermaid
sequenceDiagram
    participant D as Workshop Device
    participant B as MQTT Broker
    participant GC as GroundControl Backend
    participant DB as SQLite DB

    D->>B: publish {uid, device_id} to<br/>{device_id}/nfc or similar
    B->>GC: on_message callback
    GC->>DB: store raw scan in tag_scans
    GC->>DB: look up rfid_tags WHERE uid = ?
    DB-->>GC: tag record (or not found)
    alt Tag is registered and active
        GC->>DB: get or create Laufzettel<br/>WHERE uid = ? AND date = today
        GC->>DB: append device_id to nodes
        GC->>B: publish user info to display topic
    else Tag unknown or inactive
        GC->>DB: mark scan as unvalidated
    end
```

### Important behaviors

- Only **one** Laufzettel per `uid + date` combination is ever created
- The first scan of the day sets the `start` time
- `owner_name` and `member_id` are **copied from the tag** into the Laufzettel at creation time
- If the tag's owner name is updated later, the historical Laufzettel keeps the old value — by design

## Manual Laufzettel creation

The `/laufzettel` page has a **Neuer Laufzettel** button. Useful when:

- A scan did not happen but usage must still be recorded
- An operator needs to backfill an entry
- Testing or administrative corrections

When creating manually and the entered UID is already registered, the form auto-fills `owner_name` and `member_id` from the tag record.

## Laufzettel fields reference

| Field | Type | Set by |
|---|---|---|
| `uid` | string | Scan event or manual entry |
| `date` | date | Auto: today / Manual: operator picks |
| `start` | string | First scan time (HH:MM) |
| `owner_name` | string | Copied from tag at creation |
| `member_id` | string | Copied from tag at creation |
| `nodes` | JSON list | Appended per scan device |
| `payment_method` | string | Set on payment (`bar` / `paypal` / `karte`) |
| `paid_at` | datetime | Set on payment (UTC) |
| `created_at` | datetime | Auto |

## Material on a Laufzettel

A Laufzettel can carry many material entries. Each entry has two possible origins:

```mermaid
flowchart LR
    M["Add Material\nto Laufzettel"] --> Mode{"Mode?"}
    Mode -->|Sonstiges| FT["Name + Menge\n(Sonstiges)"]
    Mode -->|Katalog| CAT["Location →\nKategorie →\nVariante"]
    CAT --> PRICE["Auto-calculate\nprice"]
    PRICE --> STORE["Store calculated_price\n(historical snapshot)"]
    FT --> STORE2["Store name + menge\n(no price)"]
```

### Material entry fields

| Field | Free-text | Catalog-based |
|---|---|---|
| `name` | Required | From variant name |
| `menge` | Optional | Set by operator |
| `unit` | Optional | From category unit |
| `variante_id` | — | Required (FK) |
| `laenge_cm` | — | For volume pricing |
| `breite_cm` | — | For volume pricing |
| `hoehe_cm` | — | For volume pricing |
| `calculated_price` | — | Auto-computed |

## Payment flow

Once all material has been added, the detail page shows three payment buttons:

- **Bar bezahlen** — displays the total amount in a large pop-up. Confirm to lock.
- **mit PayPal bezahlen** — shows a QR code linking to your PayPal.me URL + amount. Confirm after the customer scans.
- **mit Karte bezahlen** — sends a checkout request to the paired SumUp card reader. Locks on success.

After any successful payment:
- `payment_method` and `paid_at` are written to the Laufzettel.
- The detail page shows a green locked banner with method and timestamp.
- All edit actions (info, add/edit/delete material) are disabled in the UI and rejected by the API (`409 Conflict`).

> The lock is permanent — there is no unlock flow by design.

## Why data is copied into the Laufzettel

The system intentionally copies `owner_name` and `member_id` from the tag at scan time rather than storing only the UID reference. This preserves **historical truth** — even if a card is reassigned later, past records remain accurate and auditable.

The same principle applies to `calculated_price` on material entries: the price is stored at the time of entry, not recalculated on every view.

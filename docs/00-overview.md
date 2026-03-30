# GroundControl Overview

MakerPi GroundControl is the central web and database system for managing MQTT-connected workshop devices, RFID tags, Laufzettel entries, and material tracking.

## What the system does

At a high level, the system connects four areas:

- **Workshop devices** publish MQTT messages
- **GroundControl backend** receives and stores those messages
- **SQLite database** keeps the persistent state and history
- **Web UI** lets operators manage devices, tags, Laufzettel, and the material catalog

## Main user-facing concepts

### Devices

A device is typically a Pico W or another MQTT-speaking node that publishes status or operational data. Devices are discovered automatically from MQTT topics and shown in the dashboard.

### RFID Tags

Registered RFID tags represent card holders or workshop users.

Each tag can store:

- owner name
- member ID
- notes
- active/inactive state

### Laufzettel

A Laufzettel is a day-specific usage record for a tag holder.

A Laufzettel can contain:

- date
- start time
- owner name
- member ID
- nodes/devices where the tag was used
- material entries

Laufzettel can be:

- created automatically on first NFC use of the day
- created manually from the web UI

### Material entries

Material can be added to a Laufzettel either:

- as free text
- from the material catalog

Catalog-based entries can calculate a price automatically.

### Material catalog

The material catalog is organized like this:

- **Location**
- **Category**
- **Variant**

Examples:

- `Töpferei` → `Ton` → `fein`
- `Holz-Werkstatt` → `Holz` → `Eiche`
- `FabLab` → future categories and variants

## Typical operator workflow

1. Open the dashboard and verify devices are online
2. Register RFID tags on the Tags page
3. Let devices create Laufzettel automatically, or create them manually
4. Review the Laufzettel entry
5. Add material either manually or via catalog selection
6. Use the Katalog page to maintain priceable material definitions

## Important pages

- `/` — dashboard
- `/database` — database statistics and message browsing
- `/tags` — RFID tag administration
- `/laufzettel` — Laufzettel list and manual creation
- `/laufzettel/{id}` — Laufzettel detail and material editing
- `/katalog` — material catalog management

## Important ports

- **Main app**: `8000`
- **Docs app**: `8001`

## Where to go next

- Read [Quickstart](./01-quickstart.md)
- Read [Web UI Guide](./02-web-ui.md)
- Read [Tags and Laufzettel](./03-tags-and-laufzettel.md)

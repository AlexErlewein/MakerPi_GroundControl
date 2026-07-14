# Web UI Guide

This page explains the main web pages from the perspective of someone operating the system.

## Dashboard (`/`)

The dashboard is the entry page.

Use it to:

- see if the backend is connected and alive (MQTT status)
- view open Laufzettel count
- view offline devices count
- view Spenden (donations) for the current month
- view how many members are present today (based on open Laufzettel with member ID)
- check system status for:
  - Docs server (port 8001)
  - Zigbee bridge (port 8090 + USB connection)
  - Databases/BackBlaze (Litestream + B2 connection)
  - Google Drive connection

The system status indicators show colored dots:
- **Green** = OK/connected
- **Red** = Error/offline
- **Yellow** = Warning/partial issues
- **Gray** = Unknown

Each system status label is clickable and links to the respective service.

## Database page (`/database`)

The database page is mainly for inspection and debugging.

Use it to:

- review message history
- inspect topic diversity and system usage
- check database statistics

This page is more technical than the dashboard.

## Tags page (`/tags`)

This page is for RFID tag administration.

You can:

- create a tag
- edit owner name
- edit member ID
- add notes
- activate/deactivate tags
- inspect recent scan events

This page is the primary place to maintain cardholder identity data.

## Laufzettel list (`/laufzettel`)

This page shows all Laufzettel entries.

You can:

- filter entries
- inspect who used which tag on which date
- create a new Laufzettel manually with the **Neuer Laufzettel** button

When creating manually, the UI can auto-fill owner and member ID for known UIDs.

## Laufzettel detail (`/laufzettel/{id}`)

This page is the detailed editor for one Laufzettel.

You can:

- edit owner name
- edit member ID
- edit start time
- see nodes/devices involved
- add, edit, and delete material entries

Material entry modes:

- **Sonstiges** — manual name + amount + optional unit
- **Aus Katalog** — select location/category/variant and let the system compute price

## Katalog page (`/katalog`)

This page manages the predefined material structure.

Hierarchy:

- location
- category
- variant

Examples:

- `Töpferei` → `Ton` → `fein`
- `Holz-Werkstatt` → `Holz` → `Esche`

For each category you define:

- pricing model
- display unit

For each variant you define:

- variant name
- unit price

## Mitglieder page (`/mitglieder`)

Member database management.

You can:

- view all members (synced from easyVerein or created manually)
- see each member's NFC card enrollment status
- enroll an NFC card for a member (triggers a write command to the card writer device)
- manually create or edit member records

## Kasse page (`/kasse`)

Quick-access payment screen. Allows triggering card payment from a dedicated cashier view without opening the full Laufzettel detail page.

## Device detail (`/devices/{device_id}`)

Detailed view of a single MQTT device.

Shows:

- last seen timestamp
- NFC status (OK / error)
- recent messages from the device

## Member area (`/member`)

Self-service area for members with a `role="member"` user account.

Members can:

- view their own open and historical Laufzettel
- add material to their open Laufzettel

Members **cannot** trigger payments, delete entries, or see other members' data.

## Bug report form (`/bug-report`)

Public form linked to the Plane issue tracker. Anyone on the local network can submit a bug report. Requires `plane_url` and `plane_api_token` to be configured.

## Shopify page (`/shopify`)

Integration page for Shopify inventory lookups. Requires `shopify_store` and `shopify_access_token` to be configured.

## Accounting (`/buchhaltung`)

Revenue overview for accounting purposes.

Shows: revenue split by tax rate (0%, 7%, 19%), donations (is_spende materials and manual entries), filtering by period (week/month/year).

See [Accounting](./22-accounting.md) for full documentation.

## Docs site

The docs site is separate from the main UI and should run on port `8001`.

The main UI can link to it as the long-form handbook for operators and developers.

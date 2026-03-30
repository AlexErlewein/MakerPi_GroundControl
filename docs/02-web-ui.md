# Web UI Guide

This page explains the main web pages from the perspective of someone operating the system.

## Dashboard (`/`)

The dashboard is the entry page.

Use it to:

- see if the backend is connected and alive
- inspect recently seen devices
- inspect recent MQTT messages
- get a quick overall system status

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

- **Freitext** — manual name + amount + optional unit
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

## Docs site

The docs site is separate from the main UI and should run on port `8001`.

The main UI can link to it as the long-form handbook for operators and developers.

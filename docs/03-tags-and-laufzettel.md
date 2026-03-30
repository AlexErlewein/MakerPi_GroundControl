# Tags and Laufzettel

This page explains how RFID tags and Laufzettel work together.

## Registered tags

A registered RFID tag lives in the `rfid_tags` table.

Important fields:

- `uid`
- `owner_name`
- `member_id`
- `active`
- `notes`

A tag represents a known user/cardholder.

## Recent scans

Whenever a device sends an NFC-related MQTT message, the backend can:

- store a raw scan event in `tag_scans`
- match the UID against `rfid_tags`
- mark the event as validated or unknown

## Automatic Laufzettel creation

When a known tag is used for the first time on a given day, the backend creates a new Laufzettel for that `uid + date` combination.

Important behavior:

- only one Laufzettel per `uid` and `date`
- the first use sets `start`
- the device/node is added to the `nodes` list
- owner name and member ID are copied into the Laufzettel

## Manual Laufzettel creation

The web UI also supports manual creation.

This is useful when:

- a usage record must be entered after the fact
- an MQTT/NFC scan did not happen
- an operator wants to prepare the entry manually

The UI can auto-fill owner/member data if the UID is already registered.

## Laufzettel fields

A Laufzettel typically contains:

- `uid`
- `date`
- `start`
- `owner_name`
- `member_id`
- `nodes`

## Material on a Laufzettel

A Laufzettel can contain many material entries.

There are two modes:

### Free-text material

Use this when:

- the material is unusual
- no catalog entry exists yet
- you only want to document usage quickly

### Catalog-based material

Use this when:

- the price should be calculated automatically
- the material belongs to a managed location/category/variant
- the workshop wants consistent naming and pricing

## Why data is copied into the Laufzettel

Even if a tag later changes owner name or member ID, the Laufzettel keeps the historical values stored at the time of use. This makes the usage record more stable and auditable.

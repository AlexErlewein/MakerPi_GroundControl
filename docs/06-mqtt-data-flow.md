# MQTT Data Flow

This page explains how MQTT data enters and leaves GroundControl.

## Incoming device messages

Devices publish to topics such as:

- `<device-id>/status`
- `<device-id>/data`
- `<device-id>/temp`
- `<device-id>/humidity`
- `<device-id>/alert`

The backend stores raw messages in `mqtt_messages` and updates device state in `devices`.

## NFC / tag flow

A device publishes an NFC-related payload.

The backend then:

1. parses the payload
2. extracts the UID
3. checks if the UID is a registered tag
4. stores a scan event in `tag_scans`
5. creates or updates a Laufzettel for that day
6. appends the device ID to the Laufzettel `nodes`

## Material flow

Material entries can arrive through MQTT as well.

Current expected topic pattern:

```text
{device_id}/material
```

Expected JSON payload shape:

```json
{
  "uid": "04AABBCCDD",
  "name": "PLA",
  "menge": 100
}
```

The backend tries to associate the material with the correct daily Laufzettel for the given UID.

## Outgoing MQTT messages

The backend can also publish to devices.

Examples:

- device commands
- user/tag info for displays

One recent example in the codebase is publishing user info to a display-oriented topic after NFC processing.

## Error handling

Common failure cases:

- invalid JSON payloads
- unknown tags
- missing fields in material messages
- MQTT broker unavailable

In those cases, the backend logs the event and may skip follow-up actions.

## Debugging tip

To inspect MQTT traffic locally:

```bash
mosquitto_sub -h localhost -t "#" -v
```

# 🛰️ MakerPi GroundControl

MQTT broker management and monitoring system for Raspberry Pi with web interface, including Zigbee2MQTT integration for Zigbee device support.

## Features

- **MQTT Broker**: Mosquitto broker running on Raspberry Pi
- **Zigbee2MQTT**: Bridges Zigbee devices (sensors, switches, lights) to MQTT via USB dongle
- **Web Dashboard**: Real-time monitoring of connected devices and messages
- **Data Storage**: SQLite database for message history
- **Device Tracking**: Automatic device discovery and status tracking
- **RFID Tag Management**: Register tags, validate scans, view scan history, and register unknown tags directly from scan results
- **REST API**: Full API for integration with other services

## Architecture

```
┌─────────────┐      publish      ┌──────────────┐
│  PicoW      │ ─────────────────►│   Mosquitto  │
│  (client)   │                   │   (broker)   │
└─────────────┘                   └──────────────┘
                                        ▲    │
┌─────────────┐    zigbee2mqtt/   │    │ subscribe
│  Zigbee     │    ...topics      │    │
│  Devices    │ ──►┌──────────────┴┐   │
│  (sensors,  │    │ Zigbee2MQTT   │   │
│   switches) │    │ (USB dongle)  │   │
└─────────────┘    └───────────────┘   │
                                        │
                                        ▼
                                  ┌──────────────┐
                                  │  FastAPI     │
                                  │  Backend     │
                                  └──────────────┘
                                           │
                                ┌──────────┴──────────┐
                                ▼                     ▼
                         ┌────────────┐      ┌─────────────┐
                         │   SQLite   │      │  Web UI     │
                         │  Database  │      │  (HTML/JS)  │
                         └────────────┘      └─────────────┘
```

## Quick Start

### 1. Clone on Raspberry Pi

```bash
git clone https://github.com/AlexErlewein/MakerPi_GroundControl.git
cd MakerPi_GroundControl

# Optional: Install uv for faster package installs
bash scripts/install_uv.sh

# Run setup
sudo bash scripts/setup.sh
```

### 2. Access the Dashboard

Open your browser: `http://<pi-ip>:8000`

## Project Structure

```
MakerPi_GroundControl/
├── backend/
│   └── main.py              # FastAPI application with MQTT client
├── config/
│   ├── mosquitto.conf       # MQTT broker configuration
│   └── zigbee2mqtt.yaml     # Zigbee2MQTT configuration template
├── scripts/
│   ├── setup.sh                   # Initial setup script for Pi
│   ├── deploy.sh                  # Deploy updates from dev machine
│   ├── install_uv.sh              # Install uv (fast package manager)
│   ├── migrate_add_nfc_status.py  # Database migration script
│   └── reset_database.py          # Reset database (fresh start)
├── static/
│   ├── css/
│   │   ├── style.css        # Shared styles
│   │   ├── database.css     # Database page styles
│   │   ├── device-detail.css
│   │   └── tags.css         # Tags page styles
│   └── js/
│       ├── app.js           # Dashboard frontend logic
│       ├── database.js
│       ├── device-detail.js
│       └── tags.js          # Tags page frontend logic
├── templates/
│   ├── index.html           # Main dashboard
│   ├── database.html        # Database overview
│   ├── device-detail.html   # Per-device view
│   └── tags.html            # RFID tag management
├── pyproject.toml           # Dependencies and project config (use uv)
└── README.md
```

## Development Workflow

### Local Development

```bash
# Install dependencies
uv sync

# Run locally (requires MQTT broker)
uv run uvicorn backend.main:app --reload
```

### Deploying to Pi

```bash
# Sync code only
./scripts/deploy.sh raspberrypi.local

# Sync code + update dependencies
./scripts/deploy.sh raspberrypi.local --update-deps
```

### Using uv (Faster Package Management)

The project uses [`uv`](https://github.com/astral-sh/uv) for package management. All dependencies are declared in `pyproject.toml`.

Install on Pi:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

Common commands:
```bash
uv sync                                    # install all dependencies
uv run uvicorn backend.main:app --reload   # run the app
uv run sqlite_web -H 0.0.0.0 groundcontrol.db  # run DB browser (see below)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/database` | GET | Database overview page |
| `/tags` | GET | RFID tag management page |
| `/api/status` | GET | System status (MQTT connection) |
| `/api/devices` | GET | List all registered devices |
| `/api/devices/{id}` | GET | Device detail + recent messages |
| `/api/devices/{id}` | DELETE | Delete a device |
| `/api/devices/{id}/commands` | POST | Send command to device via MQTT |
| `/api/messages` | GET | Recent messages (`?limit=100&topic=xyz`) |
| `/api/topics` | GET | List all active topics |
| `/api/tags` | GET | List all registered RFID tags |
| `/api/tags` | POST | Register a new tag |
| `/api/tags/{uid}` | PUT | Update a tag |
| `/api/tags/{uid}` | DELETE | Delete a tag |
| `/api/tags/scans` | GET | Recent tag scan events (`?limit=100`) |
| `/api/database/stats` | GET | Database statistics |
| `/api/export/devices` | GET | Export devices as CSV |
| `/api/export/messages` | GET | Export messages as CSV |

## MQTT Configuration

- **Host**: `localhost` (on Pi) or Pi's IP address
- **Port**: `1883`
- **Anonymous access**: Enabled (for local network)

### Expected MQTT Topic Structure

| Topic | Description |
|-------|-------------|
| `{device_id}/heartbeat` | Device heartbeat with NFC hardware status |
| `{device_id}/status` | Device online/offline status |
| `{device_id}/tag` | RFID tag scan event (also accepts `/nfc`) |

NFC scan payload example:
```json
{"timestamp": "1609464117", "atqa": "0x0004", "sak": "0x08", "uid_dec": 2633114887, "tag_type": "MIFARE Classic", "uid": "9CF22507"}
```

### Example MQTT Publish (PicoW)

```python
import network
import umqtt.simple

mqtt = umqtt.simple.MQTTClient("pico-w", "192.168.1.100")
mqtt.connect()
mqtt.publish("pico-w/sensors/temp", "22.5")
mqtt.disconnect()
```

## Service Management

```bash
# View service status
sudo systemctl status groundcontrol
sudo systemctl status mosquitto
sudo systemctl status zigbee2mqtt

# View logs
sudo journalctl -u groundcontrol -f
sudo journalctl -u mosquitto -f
sudo journalctl -u zigbee2mqtt -f

# Restart services
sudo systemctl restart groundcontrol
sudo systemctl restart mosquitto
sudo systemctl restart zigbee2mqtt
```

## Zigbee2MQTT

Zigbee2MQTT bridges your Zigbee USB dongle to the Mosquitto broker, making all Zigbee devices available as MQTT topics.

### Finding your USB dongle port

Run this on the Pi before and after plugging in the dongle to identify the port:

```bash
ls /dev/tty{USB,ACM}*
```

Common ports by dongle variant:
| Dongle | Chip | Adapter | Typical port |
|--------|------|---------|--------------|
| Sonoff Zigbee 3.0 USB Dongle Plus (P) | CC2652P | `znp` | `/dev/ttyUSB0` |
| Sonoff Zigbee 3.0 USB Dongle Plus-E | EFR32MG21 | `ezsp` | `/dev/ttyACM0` |

### Updating the config

Edit `/opt/zigbee2mqtt/data/configuration.yaml` on the Pi:

```yaml
serial:
  port: /dev/ttyUSB0   # ← update this
  adapter: znp         # ← change to 'ezsp' for Dongle-E
```

Then restart: `sudo systemctl restart zigbee2mqtt`

### Pairing new Zigbee devices

Temporarily enable joining, then trigger pairing mode on your device:

```bash
# Enable joining for 3 minutes
mosquitto_pub -t zigbee2mqtt/bridge/request/permit_join -m '{"value": true, "time": 180}'

# Disable joining again
mosquitto_pub -t zigbee2mqtt/bridge/request/permit_join -m '{"value": false}'
```

Or use the Zigbee2MQTT web frontend at `http://<pi-ip>:8090`.

### MQTT topics published by Zigbee2MQTT

| Topic | Description |
|-------|-------------|
| `zigbee2mqtt/<device_name>` | Device state (temperature, occupancy, etc.) |
| `zigbee2mqtt/bridge/state` | Bridge online/offline status |
| `zigbee2mqtt/bridge/devices` | List of all paired devices |
| `zigbee2mqtt/bridge/log` | Bridge log messages |

## Database

SQLite database located at: `/opt/makerpi-groundcontrol/groundcontrol.db`

### Schema

**devices** table:
- `id` - Primary key
- `device_id` - Unique device identifier
- `name` - Device name
- `last_seen` - Last activity timestamp
- `status` - Current status (online/offline/unknown)
- `nfc_ok` - NFC hardware status (1=OK, 0=Error, NULL=Unknown)
- `nfc_error` - NFC error message if applicable

**mqtt_messages** table:
- `id` - Primary key
- `topic` - MQTT topic
- `payload` - Message payload
- `qos` - Quality of Service level
- `retained` - Retained flag
- `timestamp` - Message timestamp

**rfid_tags** table:
- `id` - Primary key
- `uid` - Tag UID (e.g. `9CF22507`), unique
- `owner_name` - Name of the tag owner
- `owner_email` - Owner email (optional)
- `notes` - Free-text notes (optional)
- `active` - 1=active, 0=disabled
- `created_at` - Registration timestamp

**tag_scans** table:
- `id` - Primary key
- `uid` - Scanned tag UID
- `device_id` - Device that performed the scan
- `timestamp` - Scan timestamp
- `validated` - 1=known tag, 0=unknown
- `owner_name` - Owner name if tag was found in registry
- `tag_type` - e.g. `MIFARE Classic`
- `atqa` - ATQA value from scan payload
- `sak` - SAK value from scan payload

### Browsing the Database

Use `sqlite-web` for a web-based read/write UI:

```bash
# Bind to all interfaces so you can access it from another machine on the network
uv run sqlite_web -H 0.0.0.0 groundcontrol.db
```

Then open `http://<pi-ip>:8080` in your browser.

> Note: stop the GroundControl service first if port conflicts occur, or run sqlite-web on a different port with `-p <port>`.

### Database Migrations

When updating to a new version with schema changes, you have two options:

**Option 1: Migrate existing data** (preserves messages and devices):
```bash
cd /opt/makerpi-groundcontrol
python3 scripts/migrate_add_nfc_status.py
sudo systemctl restart groundcontrol
```

**Option 2: Reset database** (fresh start, all data lost):
```bash
cd /opt/makerpi-groundcontrol
python3 scripts/reset_database.py
sudo systemctl restart groundcontrol
```

## RFID Tag Management

The `/tags` page lets you manage a registry of known RFID tags and view all scan events.

### Registering a tag

- Click **+ Add Tag** and enter the UID, owner name, and optional email/notes.
- Or scan a tag with a device — it will appear in **Recent Scans** with an ✗ Unknown badge. Click **+ Register** on that row to open the add form with the UID pre-filled.

### How validation works

When a scan arrives on `{device_id}/tag`, the backend looks up the UID in the `rfid_tags` table:
- **Known & active** → scan is stored as `validated=true`, owner name is recorded.
- **Unknown** → scan is stored as `validated=false`, shows up highlighted in the scan list.

### Tag states

- **Active** — tag is recognised and validated on scan.
- **Disabled** — tag exists in the registry but will not be validated (treated as unknown).

## Requirements

- Raspberry Pi (3B+ or newer recommended)
- Raspberry Pi OS
- Python 3.9+
- Mosquitto MQTT Broker

## License

MIT

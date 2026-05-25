# 🛰️ MakerPi GroundControl

Comprehensive Raspberry Pi management system for a makerspace — MQTT monitoring, RFID access control, work-order tracking, material catalog, payments, and more.

## Features

- **MQTT Broker**: Mosquitto broker for device communication
- **RFID/NFC Access Control**: Member authentication with HMAC card signatures (anti-clone protection)
- **Automatic Work-Order Tracking**: NFC scans auto-create Laufzettel, track material usage, and handle payments
- **Material Catalog**: 3-level hierarchy (Location → Kategorie → Unterkategorie → Variante), CSV bulk import, flexible pricing models
- **Payment Integration**: SumUp Solo Cloud API, Payment Switch (deep-link), Wero, cash
- **easyVerein Sync**: Automatic daily member sync from easyVerein API
- **Shopify Gift Cards**: Track and adjust gift card balances via API
- **Buchhaltung (Accounting)**: Donation (Spende) and spending tracking
- **Plane Issue Tracker**: Self-hosted bug report form integration (Docker, port 3000)
- **YouTrack** (optional): Self-hosted project management (Docker, port 8081)
- **Guest Self-Service**: Public landing page for guest work-order creation
- **Member Portal**: View own Laufzettel history and account
- **Web Push Notifications**: Real-time alerts
- **PWA Support**: Service worker with offline fallback
- **Documentation Site**: Separate FastAPI-served docs from Markdown files

## Architecture

```
┌─────────────┐      publish      ┌──────────────┐
│  PicoW      │ ─────────────────►│   Mosquitto  │
│  (NFC scan) │                   │   (broker)   │
└─────────────┘                   └──────────────┘
                                         ▲    │
                                         │    │ subscribe
                                         │
                                         ▼
                                   ┌──────────────┐
                                   │  FastAPI     │
                                   │  Main App    │
                                   │  (port 8000) │
                                   └──────────────┘
                                            │
           ┌────────────────┬───────────────┼──────────────┬─────────────┐
           ▼                ▼               ▼              ▼             ▼
    ┌────────────┐   ┌────────────┐  ┌────────────┐ ┌─────────┐ ┌──────────┐
    │ auth.db    │   │ members.db │  │laufzettel.db│catalog.db│  core.db │
    │ (users,    │   │ (Mitglied, │  │ (work      │ (materials,│ (MQTT,   │
    │  sessions) │   │  RFIDTag)  │  │  orders)   │ pricing) │  devices)│
    └────────────┘   └────────────┘  └────────────┘ └─────────┘ └──────────┘
                                                      │
                                              ┌───────┴───────┐
                                              ▼               ▼
                                        ┌─────────┐     ┌──────────┐
                                        │Web UI   │     │Docs App │
                                        │(HTML/JS)│     │(Markdown)│
                                        └─────────┘     └──────────┘
                                         port 8000      port 8001
```

## Quick Start

### 1. Clone on Raspberry Pi

```bash
git clone https://github.com/AlexErlewein/MakerPi_GroundControl.git ~/Code/MakerPi_GroundControl
cd ~/Code/MakerPi_GroundControl

# Run setup (installs dependencies, Mosquitto, systemd services)
sudo bash scripts/setup.sh
```

### 2. Configure

Copy `config/config.json.example` to `config/config.json` (done automatically by setup) and fill in your settings:

```json
{
    "mqtt_broker": "localhost",
    "mqtt_port": 1883,
    "secret_key": "change-me-to-a-random-secret",
    "sumup_api_key": "sup_sk_...",
    "sumup_merchant_code": "XXXXXXXX",
    "easyverein_api_key": "...",
    "easyverein_org_id": "..."
}
```

### 3. Access the Dashboard

- **Main Dashboard**: `http://<pi-ip>:8000`
- **Documentation Site**: `http://<pi-ip>:8001`
- **Plane** (if configured): `http://<pi-ip>:3000`

## Project Structure

```
MakerPi_GroundControl/
├── backend/
│   ├── main.py              # Main FastAPI app (port 8000)
│   ├── docs_app.py          # Docs FastAPI app (port 8000)
│   ├── auth/                # Authentication, users, sessions, admin escalation
│   ├── core/                # MQTT client, devices, tag scans, SSE
│   ├── members/             # Mitglied, RFIDTag, easyVerein sync, NFC signatures
│   ├── laufzettel/          # Work orders, material usage, payments, PDF
│   ├── catalog/             # Material catalog (3-level hierarchy)
│   ├── shopify/             # Gift card management
│   ├── buchhaltung/         # Accounting (Spenden, spending)
│   ├── plane/               # Issue tracker integration
│   ├── push/                # Web push notifications
│   └── member_routes.py     # Member self-service portal
├── config/
│   ├── config.json          # Local secrets (gitignored)
│   ├── config.json.example  # Template
│   └── mosquitto.conf       # MQTT broker config
├── docs/
│   ├── 00-overview.md       # Top-down documentation
│   └── ...                  # Additional docs
├── scripts/
│   ├── setup.sh             # Initial Pi setup
│   ├── deploy.sh            # Deploy from dev machine
│   └── check_db_integrity.py # Hourly DB health monitor
├── static/
│   ├── css/                 # Stylesheets
│   └── js/                  # Frontend logic
├── templates/               # HTML templates
└── pyproject.toml           # Dependencies (uv)
```

## Development Workflow

### Local Development

```bash
# Install dependencies
uv sync

# Run main app (requires MQTT broker)
uv run uvicorn backend.main:app --reload

# Run docs app
uv run uvicorn backend.docs_app:app --reload --port 8001
```

### Deploying to Pi

```bash
# Commit and deploy (reads pi_host from config.json)
./scripts/deploy.sh

# Deploy + update dependencies
./scripts/deploy.sh --update-deps
```

### Using uv (Fast Package Manager)

The project uses [`uv`](https://github.com/astral-sh/uv) for package management.

```bash
uv sync                                  # install dependencies
uv run uvicorn backend.main:app --reload # run the app
uv run pytest                            # run tests
```

## API Endpoints

The main API is organized by module:

| Route Prefix | Description |
|--------------|-------------|
| `/` | Dashboard (admin) |
| `/dashboard` | Alternative dashboard route |
| `/database` | Device and message monitoring |
| `/devices/{id}` | Device detail |
| `/laufzettel` | Work order management |
| `/laufzettel/{id}` | Work order detail |
| `/katalog` | Material catalog |
| `/mitglieder` | Member management |
| `/tags` | RFID tag management |
| `/shopify` | Gift card tracking |
| `/buchhaltung` | Accounting |
| `/admin/users` | User management |
| `/member/` | Member self-service portal |
| `/guest/` | Guest work order forms |
| `/api/status` | System status |
| `/api/devices` | Device list and details |
| `/api/laufzettel` | Work order CRUD and payment flows |
| `/api/katalog` | Material catalog API |
| `/api/mitglieder` | Member API, easyVerein sync |
| `/api/tags` | RFID tag CRUD |
| `/api/shopify/gift-cards` | Gift card API |
| `/api/buchhaltung` | Accounting API |

See `CLAUDE.md` for detailed module architecture.

## Payment Integration

The system supports multiple payment modes, selected automatically based on configuration:

| Mode | Condition | How it works |
|---|---|---|
| **Mock** | `sumup_mock: true` | Locks immediately, no real API call |
| **SumUp Solo** | `sumup_reader_id` set | Pushes checkout to paired Solo terminal |
| **Payment Switch** | `sumup_affiliate_key` set, no reader | Generates `sumupmerchant://` deep-link |
| **Wero** | `wero_enabled: true` | Wero payment flow |
| **Cash (Bar)** | Manual entry | Admin records cash payment |

Configure in `config.json`:

```json
{
    "sumup_api_key": "sup_sk_...",
    "sumup_merchant_code": "XXXXXXXX",
    "sumup_reader_id": "",
    "sumup_affiliate_key": "your-affiliate-key",
    "sumup_mock": false,
    "wero_enabled": false,
    "wero_merchant_id": "",
    "wero_api_key": ""
}
```

See [docs/13-payments.md](docs/13-payments.md) for full details.

## Issue Trackers (Docker)

GroundControl integrates with both [Plane](https://plane.so) and [YouTrack](https://www.jetbrains.com/youtrack/) for issue tracking. Both run as Docker containers on the Pi alongside GroundControl.

### Plane (port 3000)

Self-hosted issue tracker with a public bug report form. Setup is handled by `scripts/setup.sh` automatically. If you need to set it up manually:

```bash
mkdir -p /opt/plane && cd /opt/plane
curl -fsSL https://raw.githubusercontent.com/makeplane/plane/master/docker-compose.yaml -o docker-compose.yaml
docker compose up -d
```

Configure in `config.json`:
```json
{
    "plane_url": "http://localhost:3000",
    "plane_api_token": "your-personal-api-token",
    "plane_workspace_slug": "your-workspace-slug",
    "plane_project_id": "your-project-uuid"
}
```

The bug report form is at `/bug-report`.

### YouTrack (port 8081)

[YouTrack](https://www.jetbrains.com/youtrack/) runs as a Docker container with ARM64 support (since 2025.1). Note: JetBrains does not fully guarantee ARM compatibility.

**Requirements:** 4GB+ RAM recommended (8GB preferred). The 1GB/2GB CM5 variants are too tight.

Setup is handled by `scripts/setup.sh`. Manual setup:

```bash
mkdir -p /opt/youtrack/{data,conf,logs,backups}
docker run -d \
    --name youtrack-server \
    --restart unless-stopped \
    -v /opt/youtrack/data:/opt/youtrack/data \
    -v /opt/youtrack/conf:/opt/youtrack/conf \
    -v /opt/youtrack/logs:/opt/youtrack/logs \
    -v /opt/youtrack/backups:/opt/youtrack/backups \
    -p 8081:8080 \
    jetbrains/youtrack:latest
```

First-time setup wizard will be available at `http://<pi-ip>:8081`.

## Database Architecture

The project uses **6 separate SQLite databases** (one per module), each with WAL mode enabled for crash resilience:

| Database | Purpose |
|----------|---------|
| `auth.db` | Users, bcrypt passwords, sessions |
| `members.db` | Mitglied, RFIDTag, easyVerein sync data |
| `laufzettel.db` | Laufzettel, material usage, payments |
| `catalog.db` | Location, Kategorie, Unterkategorie, Variante |
| `core.db` | MQTT messages, devices, tag scans |
| `buchhaltung.db` | Spende (donations), spending |

All DBs are in the project root directory (e.g., `/home/alex/Code/MakerPi_GroundControl/`).

### DB Integrity Monitoring

A cron job runs hourly to check database integrity and auto-recover:

```bash
# Check logs
cat /var/log/gc-db-check.log

# Run manually
python3 ~/Code/MakerPi_GroundControl/scripts/check_db_integrity.py
```

The script tries REINDEX first (fixes index corruption), then dump/reload, and as last resort renames corrupted files so init_db() creates fresh ones on startup.

## MQTT Configuration

- **Host**: `localhost` (on Pi) or Pi's IP
- **Port**: `1883`
- **Anonymous access**: Enabled (for local network)

### Expected Topic Structure

| Topic | Description |
|-------|-------------|
| `{device_id}/heartbeat` | Device heartbeat with NFC status |
| `{device_id}/status` | Online/offline status |
| `{device_id}/tag` | NFC scan event |

NFC scan payload example:
```json
{"uid": "04A3B5C2", "atqa": "0x0044", "sak": "0x00", "tag_type": "MIFARE Classic 1K"}
```

## Service Management

```bash
# View status
sudo systemctl status groundcontrol
sudo systemctl status groundcontrol-docs
sudo systemctl status mosquitto

# View logs
sudo journalctl -u groundcontrol -f
sudo journalctl -u groundcontrol-docs -f
sudo journalctl -u mosquitto -f

# Restart services
sudo systemctl restart groundcontrol
sudo systemctl restart mosquitto
```

## easyVerein Member Sync

Members are synced daily at 03:00 via APScheduler. The sync:
- Upserts Mitglieder by `member_id` (membershipNumber)
- Never overwrites `nfc_uid` or login credentials set locally
- Syncs name, email, phone, status from easyVerein

Trigger manually:
```bash
curl -X POST http://<pi-ip>:8000/api/mitglieder/sync
```

## NFC Card Security

Cards use HMAC-SHA256 signatures to bind the card UID to member data, preventing clone attacks:
- **Signature generation**: Uses SECRET_KEY + member_id + uid + name
- **Verification**: Compares computed signature against card-stored signature
- **Modes**: `permissive` (legacy cards OK) or `strict` (only signed cards)

Configure in `config.json`:
```json
{
    "nfc_signature_mode": "permissive"
}
```

## Requirements

- Raspberry Pi (3B+ or newer recommended)
- Raspberry Pi OS
- Python 3.10+
- Mosquitto MQTT Broker
- Docker (for self-hosted Plane, optional)

## License

MIT

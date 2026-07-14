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
- **Email Notifications**: SMTP-based email (e.g. signup confirmations) with Google OAuth login
- **Cloud Backups**: Litestream replication of all SQLite DBs to Backblaze B2
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
                 ┌────────────────────────┼────────────────────────┐
                 ▼                                                  ▼
        ┌─────────────────┐                                 ┌──────────────┐
        │  7 SQLite DBs   │                                 │   Web UI     │
        │ (WAL mode, see  │                                 │ (HTML/JS)    │
        │  DB section)    │                                 └──────────────┘
        └─────────────────┘                                          │
                              ┌──────────────────────────────────────┘
                              ▼
                       ┌──────────────┐
                       │   Docs App   │
                       │ (Markdown)   │
                       └──────────────┘
                        port 8001
```

The main app reads/writes **7 SQLite databases** (each in WAL mode for crash resilience):

| Database | Purpose |
|----------|---------|
| `auth.db` | Users, bcrypt passwords, sessions |
| `core.db` | MQTT messages, devices, tag scans |
| `members.db` | Mitglied, RFIDTag, easyVerein sync data |
| `laufzettel.db` | Laufzettel, material usage, payments |
| `catalog.db` | Location, Kategorie, Unterkategorie, Variante |
| `buchhaltung.db` | Spende (donations), spending |
| `push.db` | Web push subscriptions |

## Quick Start

### 1. Clone on Raspberry Pi

```bash
git clone https://github.com/AlexErlewein/MakerPi_GroundControl.git ~/Code/MakerPi_GroundControl
cd ~/Code/MakerPi_GroundControl

# Run setup (installs dependencies, Mosquitto, systemd services)
sudo bash scripts/setup.sh
```

### 2. Configure

Copy `config/config.json.example` to `config/config.json` (done automatically by setup) and fill in your settings. The example file is fully commented and documents every key; the essentials are:

```json
{
    "mqtt_broker": "localhost",
    "mqtt_port": 1883,
    "secret_key": "change-me-to-a-random-secret",
    "admin_username": "admin",
    "admin_password": "changeme",
    "sumup_api_key": "sup_sk_...",
    "sumup_merchant_code": "XXXXXXXX",
    "easyverein_api_key": "...",
    "easyverein_org_id": "..."
}
```

See [Configuration Reference](#configuration-reference) for the full list, and `config/config.json.example` for authoritative comments.

### 3. Access the Dashboard

- **Main Dashboard**: `http://<pi-ip>:8000`
- **Documentation Site**: `http://<pi-ip>:8001`

## Project Structure

```
MakerPi_GroundControl/
├── backend/
│   ├── main.py              # Main FastAPI app (port 8000)
│   ├── docs_app.py          # Docs FastAPI app (port 8001)
│   ├── member_routes.py     # Member self-service portal + Kasse
│   ├── middleware.py        # Request middleware
│   ├── config.py            # DB engines, settings loader
│   ├── db_utils.py          # Shared DB helpers
│   ├── email_utils.py / email_templates.py  # SMTP email
│   ├── gdrive.py            # Google Drive backups
│   ├── auth/                # Authentication, users, sessions, admin escalation
│   ├── core/                # MQTT client, devices, tag scans, SSE
│   ├── members/             # Mitglied, RFIDTag, easyVerein sync, NFC signatures
│   ├── laufzettel/          # Work orders, material usage, payments, PDF
│   ├── catalog/             # Material catalog (3-level hierarchy)
│   ├── shopify/             # Gift card management
│   ├── buchhaltung/         # Accounting (Spenden, spending)
│   ├── plane/               # Issue tracker integration (bug-report form)
│   └── push/                # Web push notifications
├── config/
│   ├── config.json          # Local secrets (gitignored)
│   ├── config.json.example  # Template (fully documented)
│   └── mosquitto.conf       # MQTT broker config
├── docs/                    # Markdown docs served by docs_app
├── scripts/
│   ├── setup.sh             # Initial Pi setup (installs deps, Mosquitto, systemd, cron)
│   ├── deploy.sh            # Deploy from dev machine
│   ├── check_db_integrity.py # Hourly DB health monitor
│   ├── setup-https.sh       # Nginx + mkcert HTTPS
│   └── ...                  # OAuth token gen, backups, dev helpers
├── static/                  # CSS, JS, PWA icons, manifest.json, service worker
├── templates/               # HTML templates
├── tests/                   # pytest suite
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
| `/register` | Public member signup form |
| `/tags` | RFID tag management |
| `/shopify` | Gift card tracking |
| `/kasse` | Point-of-sale (Kasse) cash register UI |
| `/buchhaltung` | Accounting |
| `/admin/users` | User management |
| `/admin/device-pairings` | NFC reader pairing |
| `/bug-report` | Public issue report form (Plane) |
| `/member/` | Member self-service portal |
| `/guest/` | Guest work order forms |
| `/api/status` | System status |
| `/api/devices`, `/api/messages`, `/api/scans`, `/api/topics` | Core MQTT data |
| `/api/auth/*` | Login, logout, session |
| `/api/laufzettel`, `/api/guest/*` | Work order CRUD and payment flows |
| `/api/katalog` | Material catalog API |
| `/api/mitglieder`, `/api/register` | Member API, easyVerein sync |
| `/api/tags` | RFID tag CRUD |
| `/api/member/*` | Member self-service API (own Laufzettel, account) |
| `/api/kasse/*` | Kasse register API |
| `/api/shopify/gift-cards`, `/api/shopify/physical-product/*` | Gift card + product API |
| `/api/buchhaltung` | Accounting API |
| `/api/push/*` | Web push subscribe/unsubscribe, VAPID key |
| `/api/bug-report` | Issue report submission |

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

## Configuration Reference

All settings live in `config/config.json` (gitignored). Copy from `config/config.json.example` — every key is commented there. Keys are grouped by concern:

| Group | Keys | Purpose |
|-------|------|---------|
| **Host / deploy** | `pi_host`, `pi_user`, `project_dir`, `tailscale_ip` | Where the Pi lives; used by `deploy.sh` |
| **MQTT** | `mqtt_broker`, `mqtt_port` | Mosquitto connection |
| **Core secrets** | `secret_key`, `admin_username`, `admin_password` | Session signing + initial admin login |
| **SumUp** | `sumup_api_key`, `sumup_merchant_code`, `sumup_reader_id`, `sumup_affiliate_key`, `sumup_mock` | Card terminal + deep-link payments |
| **Bank transfer** | `bank_iban`, `bank_bic`, `bank_account_name` | EPC/QR-code Überweisung button on Laufzettel |
| **Wero** | `wero_enabled`, `wero_mock`, `wero_merchant_id`, `wero_api_key` | Wero payment flow |
| **easyVerein** | `easyverein_api_key`, `easyverein_org_id`, `easyverein_key_expires_at`, `easyverein_registration_mock`, `easyverein_signup_url`, `membership_groups` | Member sync + public signup |
| **Readers** | `enrollment_reader_id`, `payment_reader_id` | Specific NFC readers for enrollment / payment |
| **Google Drive** | `google_drive_enabled`, `google_drive_client_secrets_file`, `google_drive_token_file`, `google_drive_root_folder_id` | DB/PDF backups to Drive |
| **Plane** | `plane_url`, `plane_api_token`, `plane_workspace_slug`, `plane_project_id` | Cloud-hosted issue tracker (`/bug-report` form) |
| **Google OAuth** | `oauth_enabled`, `oauth_google_client_id`, `oauth_google_client_secret`, `oauth_google_redirect_uri` | SSO login for members |
| **SMTP / email** | `smtp_host`, `smtp_port`, `smtp_username`, `smtp_password`, `smtp_from_email`, `public_base_url`, `smtp_starttls`, `smtp_tls` | Outbound email |
| **Shopify** | `shopify_store`, `shopify_client_id`, `shopify_client_secret`, `shopify_access_token` | Gift card balance tracking |
| **Litestream / B2** | `litestream_enabled`, `backblaze_endpoint`, `backblaze_bucket`, `backblaze_key_id`, `backblaze_application_key` | Live SQLite replication to Backblaze B2 |

**Note on issue trackers:** GroundControl previously self-hosted Plane and YouTrack in Docker on the Pi. Both have moved to cloud hosting — `scripts/setup.sh` now actively removes any leftover containers. Only the `plane_*` API keys (pointing at the cloud instance) are still used.

## Database Architecture

All DBs are in the project root directory (e.g., `/home/alex/Code/MakerPi_GroundControl/`) and use SQLite WAL mode for crash resilience. See the table under [Architecture](#architecture) for the full list.

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

- Raspberry Pi (3B+ or newer recommended; 4GB+ RAM if running Litestream backups)
- Raspberry Pi OS
- Python 3.10+
- Mosquitto MQTT Broker

## License

MIT

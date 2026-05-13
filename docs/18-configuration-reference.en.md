# Configuration Reference

All runtime settings live in a single file: `config/config.json`.
Copy `config/config.json.example` to `config/config.json` and fill in your values.
The file is loaded once at startup — restart the service after any change.

---

## Core

| Key | Default | Description |
|---|---|---|
| `secret_key` | `"fallback-secret-change-me"` | Random secret used for session signing, HMAC card signatures, and derived Mifare keys. **Change this before first use.** |
| `admin_username` | `"admin"` | Admin login username |
| `admin_password` | `"changeme"` | Admin login password — change immediately |

**Generate a strong `secret_key`:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️ Changing `secret_key` after cards have been enrolled invalidates all existing card signatures and derived Mifare sector keys. All cards must be re-enrolled.

---

## MQTT

| Key | Default | Description |
|---|---|---|
| `mqtt_broker` | `"localhost"` | Hostname or IP of the MQTT broker |
| `mqtt_port` | `1883` | MQTT port |

Mosquitto is the expected broker. On Raspberry Pi:
```bash
sudo apt install mosquitto mosquitto-clients -y
sudo systemctl enable mosquitto
```

---

## NFC Readers

| Key | Default | Description |
|---|---|---|
| `enrollment_reader_id` | `""` | MQTT device ID of the reader used to enroll member cards |
| `payment_reader_id` | `""` | MQTT device ID of the reader used at the payment checkout |
| `card_writer_id` | `""` | MQTT device ID of the PicoW that physically writes cards during enrollment |

The device ID is the first segment of any MQTT topic the PicoW publishes to, e.g. if the PicoW publishes to `Terminal-Reader/scan`, the device ID is `Terminal-Reader`. It is set in the PicoW firmware config (`config.json` on the device).

---

## NFC Tag Security

| Key | Default | Description |
|---|---|---|
| `nfc_signature_mode` | `"permissive"` | `"permissive"`: legacy cards without a signature still work. `"strict"`: only HMAC-verified cards are accepted. |
| `mifare_sector_key` | `""` | Optional 12-character hex override for the Mifare Classic sector key. Leave empty to auto-derive from `secret_key` (recommended). |

**Rollout order:**
1. Deploy with `"permissive"` — existing un-enrolled cards continue to work
2. Re-enroll cards via the Mitglieder UI (tap card on the enrollment reader)
3. Monitor the scan log — enrolled cards show `card_verified = 1`
4. Once all active cards are re-enrolled, switch to `"strict"` and restart

**DB migration** — run once on the Pi before the first deployment with NFC security:
```bash
uv run python scripts/migrate_nfc_security.py
```

See [NFC Tag Security](./16-nfc-tag-security.en.md) for the full threat model and card data layout.

---

## EasyVerein

| Key | Default | Description |
|---|---|---|
| `easyverein_api_key` | `""` | EasyVerein REST API key |
| `easyverein_org_id` | `""` | Your organisation's numeric ID in EasyVerein |
| `easyverein_signup_url` | `""` | Public membership signup URL — sent to guests by email after they create a Laufzettel |

**Where to get the API key:**
1. Log in to [easyverein.com](https://easyverein.com) as admin
2. Go to **Einstellungen → API** (Settings → API)
3. Create a new API key and copy it

**Where to find the org ID:**
The org ID is the numeric part of your EasyVerein URL, e.g. `https://easyverein.com/organizations/26355/` → org ID is `26355`.

**Signup URL:**
In EasyVerein go to **Mitglieder → Mitglied werden** (Members → Become a member) and copy the public link. Leave empty to disable the signup email.

---

## Payments — SumUp

| Key | Default | Description |
|---|---|---|
| `sumup_api_key` | `""` | SumUp API key (`sup_sk_…`) |
| `sumup_merchant_code` | `""` | Your SumUp merchant code (e.g. `M1KJN6HM`) |
| `sumup_reader_id` | `""` | SumUp card reader device ID (optional — leave empty if using QR / Wero only) |
| `sumup_affiliate_key` | `""` | SumUp affiliate key for deeplink QR codes (`sup_afk_…`) |
| `sumup_mock` | `true` | Set to `false` in production to make real payment requests |

**Where to get SumUp keys:**
1. Log in to [me.sumup.com](https://me.sumup.com)
2. Go to **API Keys** → create a key with at minimum `payments` scope
3. Your merchant code is shown in **Account → Business profile**
4. The affiliate key is under **Integrations → Affiliate**

---

## Payments — Wero

| Key | Default | Description |
|---|---|---|
| `wero_enabled` | `false` | Set to `true` to show the Wero QR payment option |
| `wero_mock` | `true` | Set to `false` in production |
| `wero_merchant_id` | `""` | Wero merchant ID |
| `wero_api_key` | `""` | Wero API key |

Contact Wero/La Banque Postale for merchant onboarding to obtain these credentials.

---

## Email (SMTP)

Email is fully optional. If `smtp_host` is empty, all email sending is silently skipped.

| Key | Default | Description |
|---|---|---|
| `smtp_host` | `""` | SMTP server hostname, e.g. `smtp.gmail.com` |
| `smtp_port` | `587` | SMTP port — `587` for STARTTLS (most providers), `465` for SSL |
| `smtp_username` | `""` | SMTP login username (usually the sender email address) |
| `smtp_password` | `""` | SMTP password or app password |
| `smtp_from_email` | `""` | The `From:` address on outgoing emails |
| `smtp_starttls` | `true` | Use STARTTLS upgrade on port 587. Set to `false` when using `smtp_tls: true` |
| `smtp_tls` | `false` | Connect with direct TLS on port 465. Set `smtp_starttls: false` when using this |

**What emails are sent:**
- **Payment receipt** — sent to the member/guest email address after a Laufzettel is paid
- **EasyVerein signup invite** — sent to guests when they submit the guest Laufzettel form (requires `easyverein_signup_url` to be set)

**Common provider settings:**

| Provider | `smtp_host` | `smtp_port` | `smtp_starttls` | `smtp_tls` |
|---|---|---|---|---|
| Gmail | `smtp.gmail.com` | `587` | `true` | `false` |
| Gmail (SSL) | `smtp.gmail.com` | `465` | `false` | `true` |
| Outlook / Office 365 | `smtp.office365.com` | `587` | `true` | `false` |
| Strato | `smtp.strato.de` | `587` | `true` | `false` |
| IONOS / 1&1 | `smtp.ionos.de` | `587` | `true` | `false` |

**Gmail note:** You cannot use your regular Google account password. Go to **Google Account → Security → 2-Step Verification → App passwords** and generate an app password specifically for GroundControl.

---

## Google Drive (PDF backup)

| Key | Default | Description |
|---|---|---|
| `google_drive_enabled` | `false` | Set to `true` to upload generated Laufzettel PDFs to Google Drive |
| `google_drive_client_secrets_file` | `"config/gdrive_client_secrets.json"` | Path to the OAuth2 client secrets JSON downloaded from Google Cloud Console |
| `google_drive_token_file` | `"config/gdrive_token.json"` | Path where the OAuth2 access token is stored after first authorisation |
| `google_drive_root_folder_id` | `""` | Google Drive folder ID where PDFs are uploaded |

**Setup:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → enable the **Google Drive API**
3. Go to **APIs & Services → Credentials → Create credentials → OAuth client ID** (type: Desktop app)
4. Download the JSON → save as `config/gdrive_client_secrets.json`
5. Run the one-time authorisation flow on the Pi:
   ```bash
   uv run python scripts/gdrive_auth.py
   ```
6. The folder ID is the last segment of any Google Drive folder URL:
   `https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRs` → ID is `1aBcDeFgHiJkLmNoPqRs`

---

## Backups — Litestream / Backblaze B2

| Key | Default | Description |
|---|---|---|
| `litestream_enabled` | `false` | Set to `true` to enable continuous SQLite backup via Litestream |
| `backblaze_endpoint` | `""` | Backblaze B2 S3-compatible endpoint, e.g. `s3.eu-central-003.backblazeb2.com` |
| `backblaze_bucket` | `""` | Name of the B2 bucket to replicate databases into |
| `backblaze_key_id` | `""` | Backblaze application key ID |
| `backblaze_application_key` | `""` | Backblaze application key secret |

**Where to get Backblaze credentials:**
1. Log in to [backblaze.com](https://www.backblaze.com) → **B2 Cloud Storage**
2. Create a bucket (private, no public access)
3. Go to **App Keys → Add a New Application Key**
   - Limit to the bucket you just created
   - Permissions: **Read and Write**
4. Copy the `keyID` and `applicationKey` immediately — the secret is only shown once
5. The endpoint is shown on the bucket details page under **Endpoint**

See [Backups](./16-backups.de.md) for the full Litestream configuration.

---

## Plane (Bug Tracker)

| Key | Default | Description |
|---|---|---|
| `plane_url` | `""` | URL of your Plane instance, e.g. `http://192.168.3.228:3001` |
| `plane_api_token` | `""` | Plane personal API token |
| `plane_workspace_slug` | `""` | Slug of the workspace, visible in the Plane URL |
| `plane_project_id` | `""` | UUID of the project where bug reports are created |

**Where to get Plane credentials:**
1. Log in to your Plane instance
2. Go to **Profile → API Tokens → Add token**
3. Workspace slug: visible in all Plane URLs after the domain, e.g. `https://plane.example.com/h3cke-groundcontrol/` → slug is `h3cke-groundcontrol`
4. Project ID: open the project → go to **Settings → Members** — the UUID is in the browser URL

---

## Shopify

| Key | Default | Description |
|---|---|---|
| `shopify_store` | `""` | Your store domain, e.g. `your-store.myshopify.com` |
| `shopify_access_token` | `""` | Shopify Admin API access token (`shpat_…`) |

**Where to get Shopify credentials:**
1. In your Shopify admin go to **Apps → Develop apps → Create an app**
2. Under **Configuration → Admin API access scopes**, enable the scopes you need (at minimum `read_products`, `read_inventory`)
3. Go to **API credentials → Install app** → copy the **Admin API access token** (only shown once)

---

## Full example

```json
{
    "secret_key": "your-random-64-char-hex-secret",
    "admin_username": "admin",
    "admin_password": "YourStrongPassword",

    "mqtt_broker": "localhost",
    "mqtt_port": 1883,

    "enrollment_reader_id": "Terminal-Reader",
    "payment_reader_id": "Terminal-Reader",
    "card_writer_id": "Terminal-Reader",
    "nfc_signature_mode": "permissive",
    "mifare_sector_key": "",

    "easyverein_api_key": "your-easyverein-api-key",
    "easyverein_org_id": "12345",
    "easyverein_signup_url": "https://easyverein.com/public/...",

    "sumup_api_key": "sup_sk_...",
    "sumup_merchant_code": "XXXXXXXX",
    "sumup_affiliate_key": "sup_afk_...",
    "sumup_mock": false,

    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "you@gmail.com",
    "smtp_password": "your-app-password",
    "smtp_from_email": "noreply@yourdomain.de",
    "smtp_starttls": true,
    "smtp_tls": false,

    "google_drive_enabled": false,
    "google_drive_client_secrets_file": "config/gdrive_client_secrets.json",
    "google_drive_token_file": "config/gdrive_token.json",
    "google_drive_root_folder_id": "",

    "litestream_enabled": false,
    "backblaze_endpoint": "s3.eu-central-003.backblazeb2.com",
    "backblaze_bucket": "your-bucket-name",
    "backblaze_key_id": "your-key-id",
    "backblaze_application_key": "your-app-key"
}
```

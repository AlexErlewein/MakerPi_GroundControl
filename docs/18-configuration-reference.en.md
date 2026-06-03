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

| Key | Env var | Default | Description |
|---|---|---|---|
| `enrollment_reader_id` | `ENROLLMENT_READER_ID` | `""` | MQTT device ID of the reader used to enroll member cards |
| `payment_reader_id` | `PAYMENT_READER_ID` | `""` | MQTT device ID of the reader used at the payment checkout |
| `card_writer_id` | `CARD_WRITER_ID` | `""` | MQTT device ID of the PicoW that physically writes cards during enrollment |

The device ID is the first segment of any MQTT topic the PicoW publishes to, e.g. if the PicoW publishes to `Terminal-Reader/scan`, the device ID is `Terminal-Reader`. It is set in the PicoW firmware config (`config.json` on the device).

---

## NFC Tag Security

| Key | Env var | Default | Description |
|---|---|---|---|
| `nfc_signature_mode` | `NFC_SIGNATURE_MODE` | `"permissive"` | `"permissive"`: legacy cards without a signature still work. `"strict"`: only HMAC-verified cards are accepted. |
| `mifare_sector_key` | `MIFARE_SECTOR_KEY` | `""` | Optional 12-character hex override for the Mifare Classic sector key. Leave empty to auto-derive from `secret_key` (recommended). |

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

| Key | Env var | Default | Description |
|---|---|---|---|
| `easyverein_api_key` | `EASYVEREIN_API_KEY` | `""` | EasyVerein REST API key |
| `easyverein_org_id` | `EASYVEREIN_ORG_ID` | `""` | Your organisation's numeric ID in EasyVerein |
| `easyverein_signup_url` | `EASYVEREIN_SIGNUP_URL` | `""` | Public membership signup URL — sent to guests by email after they create a Laufzettel |
| `easyverein_signup_redirect_url` | `EASYVEREIN_SIGNUP_REDIRECT_URL` | `""` | URL to redirect to after the guest Laufzettel form is submitted (e.g. the EasyVerein join page) |
| `easyverein_key_expires_at` | — | `""` | Expiry date of the EasyVerein API key (ISO-8601). Informational only — shown in the admin dashboard. |
| `easyverein_registration_mock` | `EASYVEREIN_REGISTRATION_MOCK` | `false` | Set to `true` to simulate the EasyVerein registration call without making a real API request. |
| `membership_groups` | — | `[]` | List of EasyVerein group names that are relevant for member status. Leave empty to accept all groups. |

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

| Key | Env var | Default | Description |
|---|---|---|---|
| `sumup_api_key` | `SUMUP_API_KEY` | `""` | SumUp API key (`sup_sk_…`) |
| `sumup_merchant_code` | `SUMUP_MERCHANT_CODE` | `""` | Your SumUp merchant code (e.g. `M1KJN6HM`) |
| `sumup_reader_id` | `SUMUP_READER_ID` | `""` | SumUp card reader device ID (optional — leave empty if using QR / Wero only) |
| `sumup_affiliate_key` | `SUMUP_AFFILIATE_KEY` | `""` | SumUp affiliate key for deeplink QR codes (`sup_afk_…`) |
| `sumup_mock` | `SUMUP_MOCK` | `true` | Set to `false` in production to make real payment requests |

**Where to get SumUp keys:**
1. Log in to [me.sumup.com](https://me.sumup.com)
2. Go to **API Keys** → create a key with at minimum `payments` scope
3. Your merchant code is shown in **Account → Business profile**
4. The affiliate key is under **Integrations → Affiliate**

---

## Payments — Wero

| Key | Env var | Default | Description |
|---|---|---|---|
| `wero_enabled` | `WERO_ENABLED` | `false` | Set to `true` to show the Wero QR payment option |
| `wero_mock` | `WERO_MOCK` | `true` | Set to `false` in production |
| `wero_merchant_id` | `WERO_MERCHANT_ID` | `""` | Wero merchant ID |
| `wero_api_key` | `WERO_API_KEY` | `""` | Wero API key |

Contact Wero/La Banque Postale for merchant onboarding to obtain these credentials.

---

## Email (SMTP)

Email is fully optional. If `smtp_host` is empty, all email sending is silently skipped.

| Key | Env var | Default | Description |
|---|---|---|---|
| `smtp_host` | `SMTP_HOST` | `""` | SMTP server hostname, e.g. `smtp.gmail.com` |
| `smtp_port` | `SMTP_PORT` | `587` | SMTP port — `587` for STARTTLS (most providers), `465` for SSL |
| `smtp_username` | `SMTP_USERNAME` | `""` | SMTP login username (usually the sender email address) |
| `smtp_password` | `SMTP_PASSWORD` | `""` | SMTP password or app password |
| `smtp_from_email` | `SMTP_FROM_EMAIL` | `""` | The `From:` address on outgoing emails |
| `smtp_starttls` | `SMTP_STARTTLS` | `true` | Use STARTTLS upgrade on port 587. Set to `false` when using `smtp_tls: true` |
| `smtp_tls` | `SMTP_TLS` | `false` | Connect with direct TLS on port 465. Set `smtp_starttls: false` when using this |
| `public_base_url` | `PUBLIC_BASE_URL` | `""` | Public base URL of the server, e.g. `https://gc.example.com`. Used to construct links in outgoing emails when the server runs behind a reverse proxy and `request.url` resolves to the internal address. Omit the trailing slash. |

### Gmail OAuth2 (Recommended for Gmail)

For Gmail accounts, OAuth2 authentication is recommended over traditional password auth.

| Key | Env var | Default | Description |
|---|---|---|---|
| `gmail_oauth_enabled` | `GMAIL_OAUTH_ENABLED` | `false` | Enable OAuth2 authentication for Gmail |
| `gmail_oauth_token_file` | `GMAIL_OAUTH_TOKEN_FILE` | `"config/gmail_oauth_token.json"` | Path to OAuth token file |
| `gmail_oauth_username` | `GMAIL_OAUTH_USERNAME` | `""` | Gmail username (for alias support like `noreply@domain.com`) |

**Setup:** See [Gmail OAuth2 Setup Guide](./GMAIL_OAUTH_SETUP.md) for detailed instructions.

**What emails are sent:**
- **Payment receipt** — sent to the member/guest email address after a Laufzettel is paid
- **EasyVerein signup invite** — sent to guests when they submit the guest Laufzettel form (requires `easyverein_signup_url` to be set)
- **Welcome email** — sent to guests when they create a Laufzettel, with direct link to their Laufzettel

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

| Key | Env var | Default | Description |
|---|---|---|---|
| `google_drive_enabled` | `GOOGLE_DRIVE_ENABLED` | `false` | Set to `true` to upload generated Laufzettel PDFs to Google Drive |
| `google_drive_client_secrets_file` | `GOOGLE_DRIVE_CLIENT_SECRETS_FILE` | `"config/gdrive_client_secrets.json"` | Path to the OAuth2 client secrets JSON downloaded from Google Cloud Console |
| `google_drive_token_file` | `GOOGLE_DRIVE_TOKEN_FILE` | `"config/gdrive_token.json"` | Path where the OAuth2 access token is stored after first authorisation |
| `google_drive_root_folder_id` | `GOOGLE_DRIVE_ROOT_FOLDER_ID` | `""` | Google Drive folder ID where PDFs are uploaded |

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

---

## Plane (Bug Tracker)

| Key | Env var | Default | Description |
|---|---|---|---|
| `plane_url` | `PLANE_URL` | `""` | URL of your Plane instance, e.g. `http://192.168.3.228:3001` |
| `plane_api_token` | `PLANE_API_TOKEN` | `""` | Plane personal API token |
| `plane_workspace_slug` | `PLANE_WORKSPACE_SLUG` | `""` | Slug of the workspace, visible in the Plane URL |
| `plane_project_id` | `PLANE_PROJECT_ID` | `""` | UUID of the project where bug reports are created |

**Where to get Plane credentials:**
1. Log in to your Plane instance
2. Go to **Profile → API Tokens → Add token**
3. Workspace slug: visible in all Plane URLs after the domain, e.g. `https://plane.example.com/h3cke-groundcontrol/` → slug is `h3cke-groundcontrol`
4. Project ID: open the project → go to **Settings** — the UUID is in the browser URL

---

## Shopify

| Key | Env var | Default | Description |
|---|---|---|---|
| `shopify_store` | `SHOPIFY_STORE` | `""` | Your store domain, e.g. `your-store.myshopify.com` |
| `shopify_access_token` | `SHOPIFY_ACCESS_TOKEN` | `""` | Shopify Admin API access token (`shpat_…`) — for statically created custom apps |
| `shopify_client_id` | `SHOPIFY_CLIENT_ID` | `""` | OAuth client ID for Dev Dashboard apps (uses `client_credentials` grant for token refresh) |
| `shopify_client_secret` | `SHOPIFY_CLIENT_SECRET` | `""` | OAuth client secret for Dev Dashboard apps |
| `shopify_physical_product_id` | `SHOPIFY_PHYSICAL_PRODUCT_ID` | `""` | Shopify product GID for the physical gift card, e.g. `gid://shopify/Product/15398922584395` |
| `shopify_gc_creation_fee` | `SHOPIFY_GC_CREATION_FEE` | `5.0` | Fixed fee (€) charged per physical gift card for card creation. Subtracted from the sale price to arrive at the actual gift card value when issuing via GroundControl. |

> **Note on `shopify_access_token` vs. `shopify_client_id`/`shopify_client_secret`:**
> Set either `shopify_access_token` (static token from an admin-created custom app) **or** `shopify_client_id` + `shopify_client_secret` (Dev Dashboard app with automatic token renewal via `client_credentials` grant). There is no need to set both.

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
    "easyverein_signup_redirect_url": "",
    "membership_groups": [],

    "sumup_api_key": "sup_sk_...",
    "sumup_merchant_code": "XXXXXXXX",
    "sumup_affiliate_key": "sup_afk_...",
    "sumup_mock": false,

    "wero_enabled": false,
    "wero_mock": true,
    "wero_merchant_id": "",
    "wero_api_key": "",

    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "you@gmail.com",
    "smtp_password": "your-app-password",
    "smtp_from_email": "noreply@yourdomain.de",
    "smtp_starttls": true,
    "smtp_tls": false,
    "public_base_url": "https://gc.yourdomain.de",

    "google_drive_enabled": false,
    "google_drive_client_secrets_file": "config/gdrive_client_secrets.json",
    "google_drive_token_file": "config/gdrive_token.json",
    "google_drive_root_folder_id": "",

    "litestream_enabled": false,
    "backblaze_endpoint": "s3.eu-central-003.backblazeb2.com",
    "backblaze_bucket": "your-bucket-name",
    "backblaze_key_id": "your-key-id",
    "backblaze_application_key": "your-app-key",

    "plane_url": "http://192.168.3.228:3001",
    "plane_api_token": "your-plane-token",
    "plane_workspace_slug": "h3cke-groundcontrol",
    "plane_project_id": "uuid-of-the-project",

    "shopify_store": "your-store.myshopify.com",
    "shopify_access_token": "shpat_...",
    "shopify_physical_product_id": "gid://shopify/Product/...",
    "shopify_gc_creation_fee": 5.0
}
```

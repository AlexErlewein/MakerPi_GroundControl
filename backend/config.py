"""Shared configuration for all modules"""

import json
import os
from pathlib import Path

# Load config file
_cfg_path = Path("config/config.json")
_cfg: dict = {}
if _cfg_path.exists():
    try:
        _cfg = json.loads(_cfg_path.read_text())
    except Exception:
        pass

# MQTT configuration
MQTT_BROKER: str = _cfg.get("mqtt_broker", "localhost")
MQTT_PORT: int = _cfg.get("mqtt_port", 1883)

# Payment configuration
SUMUP_API_KEY: str = _cfg.get("sumup_api_key", os.environ.get("SUMUP_API_KEY", ""))
SUMUP_MERCHANT_CODE: str = _cfg.get(
    "sumup_merchant_code", os.environ.get("SUMUP_MERCHANT_CODE", "")
)
SUMUP_READER_ID: str = _cfg.get(
    "sumup_reader_id", os.environ.get("SUMUP_READER_ID", "")
)
SUMUP_AFFILIATE_KEY: str = _cfg.get(
    "sumup_affiliate_key", os.environ.get("SUMUP_AFFILIATE_KEY", "")
)
SUMUP_MOCK: bool = _cfg.get(
    "sumup_mock", os.environ.get("SUMUP_MOCK", "false").lower() == "true"
)

# Wero payment configuration
WERO_ENABLED: bool = _cfg.get(
    "wero_enabled", os.environ.get("WERO_ENABLED", "false").lower() == "true"
)
WERO_MOCK: bool = _cfg.get(
    "wero_mock", os.environ.get("WERO_MOCK", "true").lower() == "true"
)
WERO_MERCHANT_ID: str = _cfg.get(
    "wero_merchant_id", os.environ.get("WERO_MERCHANT_ID", "")
)
WERO_API_KEY: str = _cfg.get("wero_api_key", os.environ.get("WERO_API_KEY", ""))

# Auth configuration
SECRET_KEY: str = _cfg.get(
    "secret_key", os.environ.get("SECRET_KEY", "fallback-secret-change-me")
)
ADMIN_USERNAME: str = _cfg.get("admin_username", "admin")
ADMIN_PASSWORD: str = _cfg.get("admin_password", "changeme")

# EasyVerein configuration
EASYVEREIN_API_KEY: str = _cfg.get(
    "easyverein_api_key", os.environ.get("EASYVEREIN_API_KEY", "")
)
EASYVEREIN_ORG_ID: str = _cfg.get(
    "easyverein_org_id", os.environ.get("EASYVEREIN_ORG_ID", "")
)
EASYVEREIN_KEY_EXPIRES_AT: str = _cfg.get("easyverein_key_expires_at", "")
EASYVEREIN_REGISTRATION_MOCK: bool = _cfg.get(
    "easyverein_registration_mock",
    os.environ.get("EASYVEREIN_REGISTRATION_MOCK", "false").lower() == "true",
)
EASYVEREIN_SIGNUP_REDIRECT_URL: str = _cfg.get(
    "easyverein_signup_redirect_url",
    os.environ.get("EASYVEREIN_SIGNUP_REDIRECT_URL", ""),
)
MEMBERSHIP_GROUPS: list = _cfg.get("membership_groups", [])

# NFC Enrollment Reader - the dedicated device used for enrolling member cards
ENROLLMENT_READER_ID: str = _cfg.get(
    "enrollment_reader_id", os.environ.get("ENROLLMENT_READER_ID", "")
)

# NFC Payment Reader - the dedicated device used for payment checkout
PAYMENT_READER_ID: str = _cfg.get(
    "payment_reader_id", os.environ.get("PAYMENT_READER_ID", "")
)

# NFC Card Writer - the dedicated device used for writing member data to cards
CARD_WRITER_ID: str = _cfg.get("card_writer_id", os.environ.get("CARD_WRITER_ID", ""))

# NFC security
# "permissive": legacy UID-only cards still work (flagged as unverified in scan log)
# "strict":     only HMAC-verified cards are accepted (set after all cards are re-enrolled)
NFC_SIGNATURE_MODE: str = _cfg.get(
    "nfc_signature_mode", os.environ.get("NFC_SIGNATURE_MODE", "permissive")
)
# Optional explicit 6-byte Mifare sector key as a 12-char hex string.
# Leave empty to auto-derive from SECRET_KEY (recommended).
MIFARE_SECTOR_KEY: str = _cfg.get(
    "mifare_sector_key", os.environ.get("MIFARE_SECTOR_KEY", "")
)

# Google Drive configuration (for automatic PDF upload)
GOOGLE_DRIVE_ENABLED: bool = _cfg.get(
    "google_drive_enabled",
    os.environ.get("GOOGLE_DRIVE_ENABLED", "false").lower() == "true",
)
GOOGLE_DRIVE_CLIENT_SECRETS_FILE: str = _cfg.get(
    "google_drive_client_secrets_file",
    os.environ.get(
        "GOOGLE_DRIVE_CLIENT_SECRETS_FILE", "config/gdrive_client_secrets.json"
    ),
)
GOOGLE_DRIVE_TOKEN_FILE: str = _cfg.get(
    "google_drive_token_file",
    os.environ.get("GOOGLE_DRIVE_TOKEN_FILE", "config/gdrive_token.json"),
)
GOOGLE_DRIVE_ROOT_FOLDER_ID: str = _cfg.get(
    "google_drive_root_folder_id",
    os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER_ID", ""),
)


# Email (SMTP) configuration
SMTP_HOST: str = _cfg.get("smtp_host", os.environ.get("SMTP_HOST", ""))
SMTP_PORT: int = _cfg.get("smtp_port", int(os.environ.get("SMTP_PORT", "587")))
SMTP_USERNAME: str = _cfg.get("smtp_username", os.environ.get("SMTP_USERNAME", ""))
SMTP_PASSWORD: str = _cfg.get("smtp_password", os.environ.get("SMTP_PASSWORD", ""))
SMTP_FROM_EMAIL: str = _cfg.get(
    "smtp_from_email", os.environ.get("SMTP_FROM_EMAIL", "")
)
SMTP_STARTTLS: bool = _cfg.get(
    "smtp_starttls", os.environ.get("SMTP_STARTTLS", "true").lower() == "true"
)
SMTP_TLS: bool = _cfg.get(
    "smtp_tls", os.environ.get("SMTP_TLS", "false").lower() == "true"
)

# Gmail OAuth2 configuration (alternative to SMTP_USERNAME/SMTP_PASSWORD)
GMAIL_OAUTH_ENABLED: bool = _cfg.get(
    "gmail_oauth_enabled",
    os.environ.get("GMAIL_OAUTH_ENABLED", "false").lower() == "true",
)
GMAIL_OAUTH_TOKEN_FILE: str = _cfg.get(
    "gmail_oauth_token_file",
    os.environ.get("GMAIL_OAUTH_TOKEN_FILE", "config/gmail_oauth_token.json"),
)
# OAuth authentication account (must be the real Google account, not an alias)
GMAIL_OAUTH_USERNAME: str = _cfg.get(
    "gmail_oauth_username",
    os.environ.get("GMAIL_OAUTH_USERNAME", SMTP_FROM_EMAIL),
)
GMAIL_OAUTH_TOKEN_FILE: str = _cfg.get(
    "gmail_oauth_token_file",
    os.environ.get("GMAIL_OAUTH_TOKEN_FILE", "config/gmail_oauth_token.json"),
)

# EasyVerein membership signup URL (sent to guests after creating a Laufzettel)
EASYVEREIN_SIGNUP_URL: str = _cfg.get(
    "easyverein_signup_url", os.environ.get("EASYVEREIN_SIGNUP_URL", "")
)

# Public base URL used when constructing links in emails (behind a reverse proxy
# request.url.netloc resolves to the internal address, not the public domain)
PUBLIC_BASE_URL: str = _cfg.get(
    "public_base_url", os.environ.get("PUBLIC_BASE_URL", "")
).rstrip("/")

# Shopify configuration
SHOPIFY_STORE: str = _cfg.get(
    "shopify_store", os.environ.get("SHOPIFY_STORE", "")
)  # e.g. "f83098-8d.myshopify.com"
SHOPIFY_CLIENT_ID: str = _cfg.get(
    "shopify_client_id", os.environ.get("SHOPIFY_CLIENT_ID", "")
)
SHOPIFY_CLIENT_SECRET: str = _cfg.get(
    "shopify_client_secret", os.environ.get("SHOPIFY_CLIENT_SECRET", "")
)
# Legacy: use a static access_token if set (admin-created custom app).
# If empty, the app will auto-refresh via client_credentials grant using
# CLIENT_ID + CLIENT_SECRET (Dev Dashboard apps).
SHOPIFY_ACCESS_TOKEN: str = _cfg.get(
    "shopify_access_token", os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
)
# Shopify product ID for the physical gift card (GID, e.g. "gid://shopify/Product/15398922584395")
SHOPIFY_PHYSICAL_PRODUCT_ID: str = _cfg.get(
    "shopify_physical_product_id",
    os.environ.get("SHOPIFY_PHYSICAL_PRODUCT_ID", ""),
)
# Fixed fee (€) charged per physical gift card for card creation; subtracted from line item price
# to arrive at the actual gift card value when issuing via GroundControl.
SHOPIFY_GC_CREATION_FEE: float = float(
    _cfg.get(
        "shopify_gc_creation_fee", os.environ.get("SHOPIFY_GC_CREATION_FEE", "5.0")
    )
)

# Plane issue tracker configuration (for public bug report form)
PLANE_URL: str = _cfg.get("plane_url", os.environ.get("PLANE_URL", ""))
PLANE_API_TOKEN: str = _cfg.get(
    "plane_api_token", os.environ.get("PLANE_API_TOKEN", "")
)
PLANE_WORKSPACE_SLUG: str = _cfg.get(
    "plane_workspace_slug", os.environ.get("PLANE_WORKSPACE_SLUG", "")
)
PLANE_PROJECT_ID: str = _cfg.get(
    "plane_project_id", os.environ.get("PLANE_PROJECT_ID", "")
)

# OAuth configuration (for Google OAuth login)
OAUTH_ENABLED: bool = _cfg.get(
    "oauth_enabled", os.environ.get("OAUTH_ENABLED", "false").lower() == "true"
)
OAUTH_GOOGLE_CLIENT_ID: str = _cfg.get(
    "oauth_google_client_id", os.environ.get("OAUTH_GOOGLE_CLIENT_ID", "")
)
OAUTH_GOOGLE_CLIENT_SECRET: str = _cfg.get(
    "oauth_google_client_secret", os.environ.get("OAUTH_GOOGLE_CLIENT_SECRET", "")
)
OAUTH_GOOGLE_REDIRECT_URI: str = _cfg.get(
    "oauth_google_redirect_uri",
    os.environ.get(
        "OAUTH_GOOGLE_REDIRECT_URI", "https://localhost:8443/auth/google/callback"
    ),
)

PROJECT_ROOT = Path(__file__).parent.parent

AUTH_DB_URL: str = f"sqlite:///{PROJECT_ROOT}/auth.db"
MEMBERS_DB_URL: str = f"sqlite:///{PROJECT_ROOT}/members.db"
LAUFZETTEL_DB_URL: str = f"sqlite:///{PROJECT_ROOT}/laufzettel.db"
CATALOG_DB_URL: str = f"sqlite:///{PROJECT_ROOT}/catalog.db"
CORE_DB_URL: str = f"sqlite:///{PROJECT_ROOT}/core.db"
BUCHHALTUNG_DB_URL: str = f"sqlite:///{PROJECT_ROOT}/buchhaltung.db"


def update_config(updates: dict) -> None:
    """Write updates to config/config.json and refresh module-level variables."""
    import sys as _sys

    cfg: dict = {}
    if _cfg_path.exists():
        try:
            cfg = json.loads(_cfg_path.read_text())
        except Exception:
            pass
    cfg.update(updates)
    _cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    mod = _sys.modules[__name__]
    for key, val in updates.items():
        var_name = key.upper()
        if hasattr(mod, var_name):
            setattr(mod, var_name, val)

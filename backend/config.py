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

# NFC Enrollment Reader - the dedicated device used for enrolling member cards
ENROLLMENT_READER_ID: str = _cfg.get(
    "enrollment_reader_id", os.environ.get("ENROLLMENT_READER_ID", "")
)

# NFC Payment Reader - the dedicated device used for payment checkout
PAYMENT_READER_ID: str = _cfg.get(
    "payment_reader_id", os.environ.get("PAYMENT_READER_ID", "")
)

# NFC Card Writer - the dedicated device used for writing member data to cards
CARD_WRITER_ID: str = _cfg.get(
    "card_writer_id", os.environ.get("CARD_WRITER_ID", "")
)

# Google Drive configuration (for automatic PDF upload)
GOOGLE_DRIVE_ENABLED: bool = _cfg.get(
    "google_drive_enabled",
    os.environ.get("GOOGLE_DRIVE_ENABLED", "false").lower() == "true",
)
GOOGLE_DRIVE_CLIENT_SECRETS_FILE: str = _cfg.get(
    "google_drive_client_secrets_file",
    os.environ.get("GOOGLE_DRIVE_CLIENT_SECRETS_FILE", "config/gdrive_client_secrets.json"),
)
GOOGLE_DRIVE_TOKEN_FILE: str = _cfg.get(
    "google_drive_token_file",
    os.environ.get("GOOGLE_DRIVE_TOKEN_FILE", "config/gdrive_token.json"),
)
GOOGLE_DRIVE_ROOT_FOLDER_ID: str = _cfg.get(
    "google_drive_root_folder_id",
    os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER_ID", ""),
)

# Backblaze B2 / Litestream configuration (for database backups)
LITESTREAM_ENABLED: bool = _cfg.get(
    "litestream_enabled",
    os.environ.get("LITESTREAM_ENABLED", "false").lower() == "true",
)
BACKBLAZE_ENDPOINT: str = _cfg.get(
    "backblaze_endpoint",
    os.environ.get("BACKBLAZE_ENDPOINT", ""),
)
BACKBLAZE_BUCKET: str = _cfg.get(
    "backblaze_bucket",
    os.environ.get("BACKBLAZE_BUCKET", ""),
)
BACKBLAZE_KEY_ID: str = _cfg.get(
    "backblaze_key_id",
    os.environ.get("BACKBLAZE_KEY_ID", ""),
)
BACKBLAZE_APPLICATION_KEY: str = _cfg.get(
    "backblaze_application_key",
    os.environ.get("BACKBLAZE_APPLICATION_KEY", ""),
)

# Shopify configuration
SHOPIFY_STORE: str = _cfg.get(
    "shopify_store", os.environ.get("SHOPIFY_STORE", "")
)  # e.g. "your-store.myshopify.com"
SHOPIFY_ACCESS_TOKEN: str = _cfg.get(
    "shopify_access_token", os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
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

# Database paths (each module owns its own)
AUTH_DB_URL: str = "sqlite:///./auth.db"
MEMBERS_DB_URL: str = "sqlite:///./members.db"
LAUFZETTEL_DB_URL: str = "sqlite:///./laufzettel.db"
CATALOG_DB_URL: str = "sqlite:///./catalog.db"
CORE_DB_URL: str = "sqlite:///./core.db"
BUCHHALTUNG_DB_URL: str = "sqlite:///./buchhaltung.db"

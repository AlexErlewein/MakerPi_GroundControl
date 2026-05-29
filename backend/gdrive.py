"""Google Drive OAuth2 client for uploading Laufzettel PDFs.

Authentication is handled via a stored token file (config/gdrive_token.json).
Run `uv run python scripts/gdrive_auth.py` once to create this file.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_drive_service = None  # cached service object


def _build_service():
    """Build and cache a Google Drive v3 service using the stored OAuth token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    from backend.config import GOOGLE_DRIVE_TOKEN_FILE

    token_path = Path(GOOGLE_DRIVE_TOKEN_FILE)
    if not token_path.exists():
        logger.warning("Google Drive token file not found: %s", token_path)
        return None

    creds = Credentials.from_authorized_user_file(
        str(token_path),
        scopes=["https://www.googleapis.com/auth/drive"],
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def get_drive_service():
    """Return the cached Drive service, or None if Drive is not configured/enabled."""
    from backend.config import GOOGLE_DRIVE_ENABLED

    if not GOOGLE_DRIVE_ENABLED:
        return None

    global _drive_service
    if _drive_service is None:
        try:
            _drive_service = _build_service()
        except Exception:
            logger.exception("Failed to build Google Drive service")
            return None
    return _drive_service


def find_or_create_folder(service, name: str, parent_id: str) -> str:
    """Return the Drive folder ID for *name* inside *parent_id*, creating it if absent."""
    query = (
        f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed = false"
    )
    result = service.files().list(q=query, fields="files(id)", pageSize=1).execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_pdf(
    pdf_bytes: bytes,
    filename: str,
    year: str,
    month_name: str,
) -> Optional[str]:
    """Upload *pdf_bytes* to Drive under <root>/<year>/<month_name>/.

    Returns the Drive file ID on success, or None if Drive is not enabled / fails.
    """
    from googleapiclient.http import MediaInMemoryUpload

    from backend.config import GOOGLE_DRIVE_ROOT_FOLDER_ID

    service = get_drive_service()
    if service is None:
        return None

    # If no root folder ID, create a "Digitale Laufzettel" folder at Drive root
    root_folder_id = GOOGLE_DRIVE_ROOT_FOLDER_ID
    if not root_folder_id:
        try:
            logger.info(
                "No google_drive_root_folder_id set, creating 'Digitale Laufzettel' folder"
            )
            root_folder_id = find_or_create_folder(
                service, "Digitale Laufzettel", "root"
            )
            logger.info("Created root folder: %s", root_folder_id)
        except Exception:
            logger.exception("Failed to create root 'Digitale Laufzettel' folder")
            return None

    try:
        year_folder_id = find_or_create_folder(service, year, root_folder_id)
        month_folder_id = find_or_create_folder(service, month_name, year_folder_id)

        media = MediaInMemoryUpload(
            pdf_bytes, mimetype="application/pdf", resumable=False
        )
        file_metadata = {"name": filename, "parents": [month_folder_id]}
        f = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        file_id = f.get("id")
        logger.info("Uploaded PDF '%s' to Drive (id=%s)", filename, file_id)
        return file_id
    except Exception:
        logger.exception("Failed to upload PDF '%s' to Google Drive", filename)
        return None

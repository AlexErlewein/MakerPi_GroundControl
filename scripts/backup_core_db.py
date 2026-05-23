#!/usr/bin/env python3
"""Daily backup of core.db to Google Drive with 3-backup rotation.

Keeps only the 3 most recent backups. Run via cron at 23:00:

    0 23 * * * cd /home/dev/Code/MakerPi_GroundControl && /home/dev/.local/bin/uv run python scripts/backup_core_db.py
"""

import sys
from pathlib import Path
from datetime import datetime
import sqlite3

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.gdrive import get_drive_service


def create_local_backup():
    """Create atomic backup of core.db using SQLite backup API."""
    db_path = PROJECT_ROOT / "core.db"
    timestamp = datetime.now().strftime("%Y%m%d")
    backup_name = f"core_db_{timestamp}.db"

    source = sqlite3.connect(str(db_path))
    backup = sqlite3.connect(":memory:")
    source.backup(backup)
    backup_bytes = b"\x00"  # Placeholder - we'll read directly

    # Get backup as bytes
    backup_bytes = b""
    for line in backup.iterdump():
        backup_bytes += f"{line};\n".encode("utf-8")

    source.close()
    backup.close()

    return backup_name, backup_bytes


def cleanup_old_backups(service, folder_id, keep=3):
    """Delete oldest backups, keeping only the most recent 'keep'."""
    from googleapiclient.errors import HttpError

    try:
        # List all core_db backups
        query = (
            f'name contains "core_db_" and "{folder_id}" in parents and trashed = false'
        )
        result = (
            service.files().list(q=query, fields="files(id,name,createdTime)").execute()
        )
        backups = result.get("files", [])

        if len(backups) <= keep:
            return

        # Sort by creation time (oldest first)
        backups.sort(key=lambda x: x.get("createdTime", ""))

        # Delete oldest
        to_delete = backups[: len(backups) - keep]
        for backup in to_delete:
            service.files().delete(fileId=backup["id"]).execute()
            print(f"Deleted old backup: {backup['name']}")
    except HttpError as e:
        print(f"Warning: Could not clean up old backups: {e}")


def main() -> None:
    print(f"[{datetime.now()}] Starting core.db backup to Google Drive...")

    # 1. Create local backup
    backup_name, backup_bytes = create_local_backup()
    print(f"Created backup: {backup_name} ({len(backup_bytes)} bytes)")

    # 2. Get Drive service
    service = get_drive_service()
    if not service:
        print("ERROR: Google Drive service not available")
        sys.exit(1)

    # 3. Find or create "Laufzettel" folder
    try:
        root_folder_id = None
        result = (
            service.files()
            .list(q="name='Laufzettel' and trashed=false", fields="files(id)")
            .execute()
        )
        files = result.get("files", [])
        if files:
            root_folder_id = files[0]["id"]
        else:
            from backend.gdrive import find_or_create_folder

            root_folder_id = find_or_create_folder(service, "Laufzettel", "root")
            print(f"Created root folder: {root_folder_id}")
    except Exception as e:
        print(f"ERROR: Could not access/create Laufzettel folder: {e}")
        sys.exit(1)

    # 4. Create "backups" subfolder
    from backend.gdrive import find_or_create_folder

    backups_folder_id = find_or_create_folder(service, "backups", root_folder_id)

    # 5. Upload backup
    from googleapiclient.http import MediaInMemoryUpload

    media = MediaInMemoryUpload(
        backup_bytes, mimetype="application/x-sqlite3", resumable=False
    )
    file_metadata = {"name": backup_name, "parents": [backups_folder_id]}
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    print(f"Uploaded to Drive: {file.get('id')}")

    # 6. Cleanup old backups (keep only 3)
    cleanup_old_backups(service, backups_folder_id, keep=3)

    print(f"[{datetime.now()}] Backup complete")


if __name__ == "__main__":
    main()

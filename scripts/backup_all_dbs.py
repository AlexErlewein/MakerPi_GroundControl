#!/usr/bin/env python3
"""Daily backup of all databases to Google Drive with 3-backup rotation.

Keeps only the 3 most recent backups per database type. Run via cron at 23:00:

    0 23 * * * cd /home/dev/Code/MakerPi_GroundControl && /home/dev/.local/bin/uv run python scripts/backup_all_dbs.py
"""

import sys
from pathlib import Path
from datetime import datetime
import sqlite3

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.gdrive import get_drive_service, find_or_create_folder
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaInMemoryUpload

# Database files to backup (relative to PROJECT_ROOT)
DATABASES = [
    "auth.db",
    "core.db",
    "members.db",
    "laufzettel.db",
    "catalog.db",
    "buchhaltung.db",
]


def create_local_backup(db_name: str):
    """Create atomic backup of a database using SQLite backup API."""
    db_path = PROJECT_ROOT / db_name
    timestamp = datetime.now().strftime("%Y%m%d")
    backup_name = f"{db_name[:-3]}_db_{timestamp}.db"

    # Validate database first
    try:
        check = sqlite3.connect(str(db_path))
        check.execute("PRAGMA integrity_check").fetchone()
        check.close()
    except Exception as e:
        print(f"ERROR: Database integrity check failed for {db_name}: {e}")
        raise

    # Use SQLite's online backup API
    source = sqlite3.connect(str(db_path))
    backup_path = PROJECT_ROOT / f"backups/{db_name[:-3]}/{backup_name}"
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    backup = sqlite3.connect(str(backup_path))
    source.backup(backup)
    backup.close()
    source.close()

    # Read backup as bytes
    backup_bytes = backup_path.read_bytes()
    backup_path.unlink()  # Clean up local temp

    return backup_name, backup_bytes


def cleanup_old_backups(service, folder_id, db_prefix: str, keep: int = 3):
    """Delete oldest backups, keeping only the most recent 'keep'."""
    try:
        # List all backups for this specific database type
        query = f'name contains "{db_prefix}_db_" and "{folder_id}" in parents and trashed = false'
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
            print(f"  Deleted old backup: {backup['name']}")
    except HttpError as e:
        print(f"  Warning: Could not clean up old backups: {e}")


def backup_database(service, db_name: str, root_folder_id: str) -> bool:
    """Backup a single database to its own subfolder. Returns True on success."""
    timestamp = datetime.now().strftime("%Y%m%d %H:%M:%S")
    print(f"[{timestamp}] Backing up {db_name}...")

    try:
        # 1. Create local backup
        db_prefix = db_name[:-3]  # Remove .db extension
        backup_name, backup_bytes = create_local_backup(db_name)
        print(f"  Created backup: {backup_name} ({len(backup_bytes)} bytes)")

        # 2. Find or create subfolder for this database
        subfolder_id = find_or_create_folder(service, db_prefix, root_folder_id)
        print(f"  Using subfolder ID: {subfolder_id}")

        # 3. Upload backup
        media = MediaInMemoryUpload(
            backup_bytes, mimetype="application/x-sqlite3", resumable=False
        )
        file_metadata = {"name": backup_name, "parents": [subfolder_id]}
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        print(f"  Uploaded to Drive: {file.get('id')}")

        # 4. Cleanup old backups (keep only 3 per database type)
        cleanup_old_backups(service, subfolder_id, db_prefix, keep=3)

        return True
    except Exception as e:
        print(f"  ERROR: Failed to backup {db_name}: {e}")
        return False


def main() -> None:
    print(f"[{datetime.now()}] Starting backup of all databases to Google Drive...")

    # 1. Get Drive service
    service = get_drive_service()
    if not service:
        print("ERROR: Google Drive service not available")
        sys.exit(1)

    # 2. Find or create "Database_Backup" folder at Drive root
    try:
        root_folder_id = None
        result = (
            service.files()
            .list(q="name='Database_Backup' and trashed=false", fields="files(id)")
            .execute()
        )
        files = result.get("files", [])
        if files:
            root_folder_id = files[0]["id"]
            print(f"Found existing Database_Backup folder: {root_folder_id}")
        else:
            root_folder_id = find_or_create_folder(service, "Database_Backup", "root")
            print(f"Created Database_Backup folder: {root_folder_id}")
    except Exception as e:
        print(f"ERROR: Could not access/create Database_Backup folder: {e}")
        sys.exit(1)

    # 3. Backup each database (continue on error)
    success_count = 0
    failed_dbs = []

    for db_name in DATABASES:
        if backup_database(service, db_name, root_folder_id):
            success_count += 1
        else:
            failed_dbs.append(db_name)

    # 4. Summary
    timestamp = datetime.now().strftime("%Y%m%d %H:%M:%S")
    print(f"[{timestamp}] Backup summary: {success_count}/{len(DATABASES)} successful")

    if failed_dbs:
        print(f"Failed databases: {', '.join(failed_dbs)}")
        sys.exit(1)  # Exit with error if any backups failed
    else:
        print(f"[{timestamp}] All backups complete")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Migration script to add NFC status columns to the devices table.
Run this on the Raspberry Pi to update the existing database.
"""

import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "groundcontrol.db"

def migrate():
    """Add nfc_ok and nfc_error columns to devices table"""
    print(f"Using database: {DB_PATH}")

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(devices)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns: {columns}")

        # Add nfc_ok column if it doesn't exist
        if "nfc_ok" not in columns:
            print("Adding nfc_ok column...")
            cursor.execute("ALTER TABLE devices ADD COLUMN nfc_ok INTEGER")
            print("✓ Added nfc_ok column")
        else:
            print("✓ nfc_ok column already exists")

        # Add nfc_error column if it doesn't exist
        if "nfc_error" not in columns:
            print("Adding nfc_error column...")
            cursor.execute("ALTER TABLE devices ADD COLUMN nfc_error TEXT")
            print("✓ Added nfc_error column")
        else:
            print("✓ nfc_error column already exists")

        conn.commit()
        print("\n✅ Migration completed successfully!")

        # Show updated schema
        cursor.execute("PRAGMA table_info(devices)")
        print("\nUpdated schema:")
        for row in cursor.fetchall():
            print(f"  - {row[1]} ({row[2]})")

    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

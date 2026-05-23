#!/usr/bin/env python3
"""Migration script to add 3VL signature columns to tag_scans table."""

import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "core.db"


def migrate():
    """Add 3VL signature columns to tag_scans table if they don't exist."""

    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check current columns
        cursor.execute("PRAGMA table_info(tag_scans)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        print(f"📊 Existing columns: {sorted(existing_columns)}")

        # Columns to add
        columns_to_add = {
            "card_member_id": "STRING",
            "card_name": "STRING",
            "card_email": "STRING",
            "card_signature": "STRING",
            "card_verified": "INTEGER",
        }

        # Add missing columns
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                alter_sql = f"ALTER TABLE tag_scans ADD COLUMN {col_name} {col_type}"
                print(f"✅ Adding column: {col_name} ({col_type})")
                cursor.execute(alter_sql)
            else:
                print(f"⏭️  Column already exists: {col_name}")

        conn.commit()
        print("\n✨ Migration completed successfully!")
        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    exit(0 if success else 1)

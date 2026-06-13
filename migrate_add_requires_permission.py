#!/usr/bin/env python3
"""Migration script to add requires_permission column to devices table."""

import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "core.db"


def migrate():
    """Add requires_permission column to devices table if it doesn't exist."""

    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check current columns
        cursor.execute("PRAGMA table_info(devices)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        print(f"📊 Existing columns: {sorted(existing_columns)}")

        # Column to add
        column_name = "requires_permission"
        column_type = "INTEGER"
        default_value = 1  # Default to requiring permission for backward compatibility

        if column_name not in existing_columns:
            alter_sql = f"ALTER TABLE devices ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
            print(
                f"✅ Adding column: {column_name} ({column_type} DEFAULT {default_value})"
            )
            cursor.execute(alter_sql)

            # Update existing devices to have the default value
            update_sql = f"UPDATE devices SET {column_name} = {default_value} WHERE {column_name} IS NULL"
            cursor.execute(update_sql)
            print(f"✅ Updated existing devices with default value: {default_value}")
        else:
            print(f"⏭️  Column already exists: {column_name}")

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

#!/usr/bin/env python3
"""
Reset the database - WARNING: This will delete all data!
Use this if you prefer to start fresh rather than migrate.
"""

from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "groundcontrol.db"


def reset_database():
    """Delete and recreate the database"""
    print(f"Database path: {DB_PATH}")

    if DB_PATH.exists():
        confirm = input(
            "⚠️  This will DELETE all existing data. Type 'yes' to confirm: "
        )
        if confirm.lower() != "yes":
            print("Cancelled.")
            return

        print("Deleting existing database...")
        DB_PATH.unlink()
        print("✓ Database deleted")

    print(
        "\n✅ Database reset complete. Restart the application to recreate the database."
    )
    print("   The new schema will include nfc_ok and nfc_error columns.")


if __name__ == "__main__":
    reset_database()

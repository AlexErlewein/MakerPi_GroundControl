#!/usr/bin/env python3
"""
Migration script to add missing guest columns to laufzettel table
"""

import sqlite3
import sys
from pathlib import Path

def migrate_add_guest_columns():
    """Add missing guest columns to laufzettel table"""
    
    project_root = Path(__file__).parent
    db_path = project_root / "laufzettel.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current columns
        cursor.execute("PRAGMA table_info(laufzettel)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add missing columns
        migrations = [
            ("guest_address", "TEXT"),
            ("guest_nfc_uid", "TEXT"),  # This might already exist from previous migration
        ]
        
        for column_name, column_type in migrations:
            if column_name not in columns:
                print(f"Adding {column_name} column...")
                cursor.execute(f"ALTER TABLE laufzettel ADD COLUMN {column_name} {column_type}")
            else:
                print(f"{column_name} column already exists")
        
        # Create indexes for performance
        indexes = [
            ("idx_laufzettel_guest_address", "guest_address"),
            ("idx_laufzettel_guest_nfc_uid", "guest_nfc_uid"),
        ]
        
        for index_name, column_name in indexes:
            if column_name in columns:
                print(f"Creating index {index_name}...")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON laufzettel({column_name})")
        
        conn.commit()
        conn.close()
        
        print("Migration completed successfully")
        
        # Verify the migration
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(laufzettel)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"\nUpdated laufzettel table columns ({len(columns)} total):")
        for col in sorted(columns):
            print(f"  {col}")
        conn.close()
        
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = migrate_add_guest_columns()
    sys.exit(0 if success else 1)

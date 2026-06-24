#!/usr/bin/env python3
"""Migration script to add guest_nfc_uid column to laufzettel table"""

import sqlite3
import sys
from pathlib import Path

def migrate_add_guest_nfc_uid():
    project_root = Path(__file__).parent
    db_path = project_root / "laufzettel.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(laufzettel)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'guest_nfc_uid' in columns:
            print("guest_nfc_uid column already exists")
            conn.close()
            return True
        
        print("Adding guest_nfc_uid column...")
        cursor.execute("ALTER TABLE laufzettel ADD COLUMN guest_nfc_uid TEXT")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_laufzettel_guest_nfc_uid ON laufzettel(guest_nfc_uid)")
        
        conn.commit()
        conn.close()
        print("Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = migrate_add_guest_nfc_uid()
    sys.exit(0 if success else 1)

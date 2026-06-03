"""Migration: add guest_address column to laufzettel table"""

import sqlite3
from pathlib import Path

DB_PATH = Path("laufzettel.db")

if not DB_PATH.exists():
    print(f"Database not found: {DB_PATH}")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(laufzettel)")
columns = [row[1] for row in cur.fetchall()]

added = []

if "guest_address" not in columns:
    cur.execute("ALTER TABLE laufzettel ADD COLUMN guest_address TEXT")
    added.append("guest_address")

if added:
    conn.commit()
    print(f"Added columns to laufzettel: {', '.join(added)}")
else:
    print("All columns already exist – nothing to do.")

conn.close()

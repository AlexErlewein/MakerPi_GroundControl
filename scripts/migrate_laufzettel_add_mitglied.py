"""Migration: add mitglied_id and created_at columns to laufzettel table"""

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

if "mitglied_id" not in columns:
    cur.execute("ALTER TABLE laufzettel ADD COLUMN mitglied_id INTEGER")
    added.append("mitglied_id")

if "created_at" not in columns:
    cur.execute("ALTER TABLE laufzettel ADD COLUMN created_at DATETIME")
    added.append("created_at")

if added:
    conn.commit()
    print(f"Added columns to laufzettel: {', '.join(added)}")
else:
    print("All columns already exist – nothing to do.")

conn.close()

"""Migration: add nfc_uid column to mitglieder table"""

import sqlite3
from pathlib import Path

DB_PATH = Path("members.db")

if not DB_PATH.exists():
    print(f"Database not found: {DB_PATH}")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(mitglieder)")
columns = [row[1] for row in cur.fetchall()]

if "nfc_uid" in columns:
    print("Column 'nfc_uid' already exists – nothing to do.")
else:
    # SQLite does not support ADD COLUMN ... UNIQUE directly
    cur.execute("ALTER TABLE mitglieder ADD COLUMN nfc_uid TEXT")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_mitglieder_nfc_uid ON mitglieder (nfc_uid) WHERE nfc_uid IS NOT NULL")
    conn.commit()
    print("Column 'nfc_uid' added to mitglieder table with unique index.")

conn.close()

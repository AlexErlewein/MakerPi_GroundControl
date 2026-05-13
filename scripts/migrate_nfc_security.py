"""Migration: add card_signature and card_verified columns to tag_scans table.

Run once on the Pi before deploying the NFC security update:
    uv run python scripts/migrate_nfc_security.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("core.db")

if not DB_PATH.exists():
    print(f"Database not found: {DB_PATH}")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(tag_scans)")
columns = [row[1] for row in cur.fetchall()]

added = []

if "card_signature" not in columns:
    cur.execute("ALTER TABLE tag_scans ADD COLUMN card_signature TEXT")
    added.append("card_signature")

if "card_verified" not in columns:
    cur.execute("ALTER TABLE tag_scans ADD COLUMN card_verified INTEGER")
    added.append("card_verified")

if added:
    conn.commit()
    print(f"Added columns to tag_scans: {', '.join(added)}")
else:
    print("Columns already exist – nothing to do.")

conn.close()

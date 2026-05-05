"""Migration: add payment_transaction_id and payment_notes to laufzettel table"""

import sqlite3
import os

DB_PATH = os.environ.get(
    "LAUFZETTEL_DB",
    os.path.join(os.path.dirname(__file__), "..", "laufzettel.db"),
)


def run():
    db_path = os.path.abspath(DB_PATH)
    print(f"Migrating: {db_path}")
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    existing = {row[1] for row in cur.execute("PRAGMA table_info(laufzettel)")}

    if "payment_transaction_id" not in existing:
        cur.execute("ALTER TABLE laufzettel ADD COLUMN payment_transaction_id VARCHAR")
        print("  + payment_transaction_id")
    else:
        print("  = payment_transaction_id already exists")

    if "payment_notes" not in existing:
        cur.execute("ALTER TABLE laufzettel ADD COLUMN payment_notes VARCHAR")
        print("  + payment_notes")
    else:
        print("  = payment_notes already exists")

    con.commit()
    con.close()
    print("Done.")


if __name__ == "__main__":
    run()

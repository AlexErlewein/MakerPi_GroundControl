"""Laufzettel database - owns laufzettel.db"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config import LAUFZETTEL_DB_URL
from .models import Base

engine = create_engine(LAUFZETTEL_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate(conn):
    """Add columns that may be missing from databases created before the model was updated."""
    cur = conn.cursor()

    # ── 1. Add missing columns (safe even if already present) ─────────────────
    cur.execute("PRAGMA table_info(laufzettel)")
    existing = {row[1] for row in cur.fetchall()}
    for col, sql in [
        ("mitglied_id", "ALTER TABLE laufzettel ADD COLUMN mitglied_id INTEGER"),
        ("created_at", "ALTER TABLE laufzettel ADD COLUMN created_at DATETIME"),
        (
            "payment_transaction_id",
            "ALTER TABLE laufzettel ADD COLUMN payment_transaction_id VARCHAR",
        ),
        ("payment_notes", "ALTER TABLE laufzettel ADD COLUMN payment_notes VARCHAR"),
    ]:
        if col not in existing:
            cur.execute(sql)

    cur.execute("PRAGMA table_info(laufzettel_material)")
    existing_mat = {row[1] for row in cur.fetchall()}
    if "tax_rate" not in existing_mat:
        cur.execute("ALTER TABLE laufzettel_material ADD COLUMN tax_rate REAL")

    # ── 2. Drop UNIQUE(uid, date) constraint if present ────────────────────────
    # SQLite doesn't support DROP CONSTRAINT – requires table recreation.
    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='laufzettel'"
    )
    row = cur.fetchone()
    if row and "uq_laufzettel_uid_date" in (row[0] or ""):
        cur.executescript("""
            PRAGMA foreign_keys = OFF;

            CREATE TABLE laufzettel_new (
                id                      INTEGER NOT NULL PRIMARY KEY,
                uid                     VARCHAR,
                date                    DATE,
                start                   DATETIME,
                owner_name              VARCHAR,
                member_id               VARCHAR,
                mitglied_id             INTEGER,
                nodes                   TEXT    DEFAULT '[]',
                payment_method          VARCHAR,
                paid_at                 DATETIME,
                payment_transaction_id  VARCHAR,
                payment_notes           VARCHAR,
                created_at              DATETIME
            );

            INSERT INTO laufzettel_new
                SELECT id, uid, date, start, owner_name, member_id, mitglied_id,
                       nodes, payment_method, paid_at, payment_transaction_id,
                       payment_notes, created_at
                FROM laufzettel;

            DROP TABLE laufzettel;
            ALTER TABLE laufzettel_new RENAME TO laufzettel;

            CREATE INDEX IF NOT EXISTS ix_laufzettel_id         ON laufzettel (id);
            CREATE INDEX IF NOT EXISTS ix_laufzettel_uid        ON laufzettel (uid);
            CREATE INDEX IF NOT EXISTS ix_laufzettel_date       ON laufzettel (date);
            CREATE INDEX IF NOT EXISTS ix_laufzettel_mitglied_id ON laufzettel (mitglied_id);

            PRAGMA foreign_keys = ON;
        """)

    conn.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        _migrate(conn.connection.driver_connection)

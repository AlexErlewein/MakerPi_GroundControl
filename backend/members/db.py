"""Members database - owns members.db"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config import MEMBERS_DB_URL
from .models import Base

engine = create_engine(MEMBERS_DB_URL, connect_args={"check_same_thread": False})
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
    cur.execute("PRAGMA table_info(mitglieder)")
    existing = {row[1] for row in cur.fetchall()}
    migrations = [
        ("login_username", "ALTER TABLE mitglieder ADD COLUMN login_username TEXT"),
        ("login_password_hash", "ALTER TABLE mitglieder ADD COLUMN login_password_hash TEXT"),
        ("nfc_uid", "ALTER TABLE mitglieder ADD COLUMN nfc_uid TEXT"),
    ]
    for col, sql in migrations:
        if col not in existing:
            cur.execute(sql)
    # Create the unique index on nfc_uid if it doesn't exist
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_mitglieder_nfc_uid "
        "ON mitglieder (nfc_uid) WHERE nfc_uid IS NOT NULL"
    )
    conn.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        _migrate(conn.connection.driver_connection)

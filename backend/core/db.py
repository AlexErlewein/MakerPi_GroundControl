"""Core database - owns core.db"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from backend.config import CORE_DB_URL
from .models import Base

engine = create_engine(CORE_DB_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA wal_autocheckpoint=100")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.db_utils import check_and_recover_engine
    check_and_recover_engine(engine)
    Base.metadata.create_all(bind=engine)
    # Auto-migrate: add card data columns to tag_scans if missing
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(tag_scans)"))]
        for col in ("card_member_id", "card_name", "card_email", "card_signature"):
            if col not in cols:
                conn.execute(text(f"ALTER TABLE tag_scans ADD COLUMN {col} TEXT"))
        if "card_verified" not in cols:
            conn.execute(text("ALTER TABLE tag_scans ADD COLUMN card_verified INTEGER"))
        conn.commit()

        # Auto-migrate: add requires_permission to devices if missing (default 1,
        # i.e. require permission, for backward compatibility with pre-existing rows).
        device_cols = [
            r[1] for r in conn.execute(text("PRAGMA table_info(devices)"))
        ]
        if "requires_permission" not in device_cols:
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN requires_permission INTEGER DEFAULT 1"
                )
            )
            conn.execute(
                text(
                    "UPDATE devices SET requires_permission = 1 "
                    "WHERE requires_permission IS NULL"
                )
            )
        conn.commit()

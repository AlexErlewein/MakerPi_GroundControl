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
    Base.metadata.create_all(bind=engine)
    # Auto-migrate: add card data columns to tag_scans if missing
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(tag_scans)"))]
        for col in ("card_member_id", "card_name", "card_email"):
            if col not in cols:
                conn.execute(text(f"ALTER TABLE tag_scans ADD COLUMN {col} TEXT"))
        conn.commit()

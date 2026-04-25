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
    cur.execute("PRAGMA table_info(laufzettel)")
    existing = {row[1] for row in cur.fetchall()}
    migrations = [
        ("mitglied_id", "ALTER TABLE laufzettel ADD COLUMN mitglied_id INTEGER"),
        ("created_at", "ALTER TABLE laufzettel ADD COLUMN created_at DATETIME"),
    ]
    for col, sql in migrations:
        if col not in existing:
            cur.execute(sql)
    conn.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        _migrate(conn.connection.driver_connection)

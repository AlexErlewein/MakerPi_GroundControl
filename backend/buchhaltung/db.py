from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .models import Base

BUCHHALTUNG_DB_URL = "sqlite:///./buchhaltung.db"
engine = create_engine(BUCHHALTUNG_DB_URL, connect_args={"check_same_thread": False})


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

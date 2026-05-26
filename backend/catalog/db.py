"""Catalog database - owns catalog.db"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from backend.config import CATALOG_DB_URL
from .models import Base

engine = create_engine(CATALOG_DB_URL, connect_args={"check_same_thread": False})


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
    with engine.connect() as conn:
        try:
            conn.execute(
                text(
                    "ALTER TABLE material_kategorie ADD COLUMN tax_rate REAL DEFAULT 19.0"
                )
            )
            conn.commit()
        except Exception:
            pass

        # Add unterkategorie_id to material_variante
        try:
            conn.execute(
                text(
                    "ALTER TABLE material_variante ADD COLUMN unterkategorie_id INTEGER"
                )
            )
            conn.commit()
        except Exception:
            pass

        # Auto-migrate: create "Standard" Unterkategorie for each Kategorie that has
        # Varianten without unterkategorie_id
        try:
            conn.execute(
                text("""
                INSERT INTO material_unterkategorie (kategorie_id, name, pricing_model, unit, tax_rate)
                SELECT k.id, 'Standard', k.pricing_model, k.unit, COALESCE(k.tax_rate, 19.0)
                FROM material_kategorie k
                WHERE EXISTS (SELECT 1 FROM material_variante v WHERE v.kategorie_id = k.id AND v.unterkategorie_id IS NULL)
                AND NOT EXISTS (SELECT 1 FROM material_unterkategorie u WHERE u.kategorie_id = k.id)
            """)
            )
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(
                text("""
                UPDATE material_variante
                SET unterkategorie_id = (
                    SELECT u.id FROM material_unterkategorie u WHERE u.kategorie_id = material_variante.kategorie_id LIMIT 1
                )
                WHERE unterkategorie_id IS NULL AND kategorie_id IS NOT NULL
            """)
            )
            conn.commit()
        except Exception:
            pass

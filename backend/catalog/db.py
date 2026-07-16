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
    from backend.db_utils import check_and_recover_engine
    check_and_recover_engine(engine)
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

        try:
            conn.execute(
                text(
                    "ALTER TABLE material_unterkategorie ADD COLUMN is_spende INTEGER DEFAULT 0"
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

        # Add per-variant pricing_model, unit, tax_rate, is_spende columns
        try:
            conn.execute(
                text(
                    "ALTER TABLE material_variante ADD COLUMN pricing_model TEXT DEFAULT 'per_unit'"
                )
            )
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(
                text(
                    "ALTER TABLE material_variante ADD COLUMN unit TEXT"
                )
            )
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(
                text(
                    "ALTER TABLE material_variante ADD COLUMN tax_rate REAL DEFAULT 19.0"
                )
            )
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(
                text(
                    "ALTER TABLE material_variante ADD COLUMN is_spende INTEGER DEFAULT 0"
                )
            )
            conn.commit()
        except Exception:
            pass

        # Backfill per-variant pricing from the parent subcategory where a variant
        # has no own value. Mirrors the legacy migrate_remove_subcategory_pricing.py.
        try:
            conn.execute(
                text(
                    """
                    UPDATE material_variante
                    SET pricing_model = COALESCE(material_variante.pricing_model, material_unterkategorie.pricing_model, 'per_unit'),
                        unit = COALESCE(material_variante.unit, material_unterkategorie.unit),
                        tax_rate = COALESCE(material_variante.tax_rate, material_unterkategorie.tax_rate, 19.0),
                        is_spende = COALESCE(material_variante.is_spende, material_unterkategorie.is_spende, 0)
                    FROM material_unterkategorie
                    WHERE material_variante.unterkategorie_id = material_unterkategorie.id
                      AND (material_variante.pricing_model IS NULL OR material_variante.unit IS NULL OR
                           material_variante.tax_rate IS NULL OR material_variante.is_spende IS NULL)
                    """
                )
            )
            conn.commit()
        except Exception:
            pass

        # Variants linked directly to a Kategorie (legacy, no Unterkategorie):
        # fall back to the Kategorie's vestigial pricing fields.
        try:
            conn.execute(
                text(
                    """
                    UPDATE material_variante
                    SET pricing_model = COALESCE(material_variante.pricing_model, material_kategorie.pricing_model, 'per_unit'),
                        unit = COALESCE(material_variante.unit, material_kategorie.unit),
                        tax_rate = COALESCE(material_variante.tax_rate, material_kategorie.tax_rate, 19.0),
                        is_spende = COALESCE(material_variante.is_spende, 0)
                    FROM material_kategorie
                    WHERE material_variante.kategorie_id = material_kategorie.id
                      AND material_variante.unterkategorie_id IS NULL
                      AND (material_variante.pricing_model IS NULL OR material_variante.unit IS NULL OR
                           material_variante.tax_rate IS NULL OR material_variante.is_spende IS NULL)
                    """
                )
            )
            conn.commit()
        except Exception:
            pass

        # Drop legacy per-subcategory pricing fields now that pricing lives on
        # the variant itself. SQLite >=3.35 supports DROP COLUMN.
        try:
            ukat_cols = [
                r[1] for r in conn.execute(
                    text("PRAGMA table_info(material_unterkategorie)")
                )
            ]
            if "pricing_model" in ukat_cols:
                conn.execute(
                    text(
                        "ALTER TABLE material_unterkategorie DROP COLUMN pricing_model"
                    )
                )
            if "unit" in ukat_cols:
                conn.execute(
                    text("ALTER TABLE material_unterkategorie DROP COLUMN unit")
                )
            conn.commit()
        except Exception:
            pass

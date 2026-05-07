from datetime import datetime, timezone
import logging
from .db import SessionLocal
from .models import Verkauf, Spende

logger = logging.getLogger(__name__)

_SPENDE_NAMES = {"spende", "donation", "spenden"}


def _is_spende(name: str | None) -> bool:
    return (name or "").strip().lower() in _SPENDE_NAMES


def record_laufzettel_payment(laufzettel, materials: list):
    """Record paid Laufzettel line items into buchhaltung.db. Never raises."""
    if not materials:
        return
    try:
        db = SessionLocal()
        try:
            paid_at = laufzettel.paid_at or datetime.now(timezone.utc)
            for mat in materials:
                if _is_spende(mat.name):
                    s = Spende(
                        amount=mat.calculated_price or 0.0,
                        donor_name=laufzettel.owner_name or None,
                        date=paid_at,
                        notes=f"Via Laufzettel #{laufzettel.id}",
                    )
                    db.add(s)
                else:
                    v = Verkauf(
                        laufzettel_id=laufzettel.id,
                        paid_at=paid_at,
                        payment_method=laufzettel.payment_method,
                        variante_id=mat.variante_id,
                        variante_name=mat.name,
                        menge=mat.menge,
                        unit=mat.unit,
                        calculated_price=mat.calculated_price or 0.0,
                        tax_rate=mat.tax_rate,
                        member_id=laufzettel.member_id,
                        owner_name=laufzettel.owner_name,
                    )
                    db.add(v)
            db.commit()
            logger.info(
                "[BUCHHALTUNG] Recorded %d line items for Laufzettel #%s",
                len(materials),
                laufzettel.id,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        logger.error(
            "[BUCHHALTUNG] Failed to record payment for Laufzettel #%s: %s",
            laufzettel.id,
            e,
        )

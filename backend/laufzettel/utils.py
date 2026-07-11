"""Utility functions for laufzettel lifecycle management."""

import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from .models import DeviceSession, Laufzettel, LaufzettelMaterial

logger = logging.getLogger(__name__)


def handle_stale_laufzettel(mitglied_id: int, db: Session, today: date = None) -> dict:
    """
    Check for and handle open laufzettel from previous days for a given member.

    Rules:
    - Empty stale laufzettel (no materials) → delete silently
    - Non-empty stale laufzettel → copy all materials into a new laufzettel for today,
      then mark the old one as payment_method='closed' (not paid, just carried over)

    Multiple stale laufzettel are all handled; all non-empty ones are consolidated into
    one today-laufzettel (created once, reused for subsequent stale ones).

    Returns a dict:
      {"action": "none"}
      {"action": "deleted", "results": [...]}
      {"action": "carried_over", "new_laufzettel": <Laufzettel>, "results": [...]}
    """
    if not mitglied_id:
        return {"action": "none"}

    if today is None:
        today = date.today()

    stale_list = (
        db.query(Laufzettel)
        .filter(
            Laufzettel.mitglied_id == mitglied_id,
            Laufzettel.payment_method.is_(None),
            Laufzettel.deleted_at.is_(None),
            Laufzettel.date < today,
        )
        .order_by(Laufzettel.date.asc())
        .all()
    )

    if not stale_list:
        return {"action": "none"}

    results = []
    today_lz = None

    for stale_lz in stale_list:
        materials = (
            db.query(LaufzettelMaterial)
            .filter(LaufzettelMaterial.laufzettel_id == stale_lz.id)
            .all()
        )

        if not materials:
            logger.info(
                "Soft-deleting empty stale laufzettel id=%s (date=%s) for mitglied_id=%s",
                stale_lz.id,
                stale_lz.date,
                mitglied_id,
            )
            stale_lz.deleted_at = datetime.now(timezone.utc)
            results.append({"action": "deleted", "laufzettel_id": stale_lz.id})
        else:
            # Ensure we have a today-laufzettel to carry into
            if today_lz is None:
                today_lz = (
                    db.query(Laufzettel)
                    .filter(
                        Laufzettel.mitglied_id == mitglied_id,
                        Laufzettel.payment_method.is_(None),
                        Laufzettel.deleted_at.is_(None),
                        Laufzettel.date == today,
                    )
                    .first()
                )

                if today_lz is None:
                    today_lz = Laufzettel(
                        uid=stale_lz.uid,
                        date=today,
                        start=datetime.now(timezone.utc),
                        owner_name=stale_lz.owner_name,
                        member_id=stale_lz.member_id,
                        mitglied_id=stale_lz.mitglied_id,
                        nodes=stale_lz.nodes,
                    )
                    db.add(today_lz)
                    db.flush()
                    logger.info(
                        "Created carry-over laufzettel id=%s for mitglied_id=%s",
                        today_lz.id,
                        mitglied_id,
                    )

            # Copy all materials from stale into today_lz
            for mat in materials:
                new_mat = LaufzettelMaterial(
                    laufzettel_id=today_lz.id,
                    name=mat.name,
                    menge=mat.menge,
                    variante_id=mat.variante_id,
                    unit=mat.unit,
                    laenge_cm=mat.laenge_cm,
                    breite_cm=mat.breite_cm,
                    hoehe_cm=mat.hoehe_cm,
                    calculated_price=mat.calculated_price,
                    tax_rate=mat.tax_rate,
                )
                db.add(new_mat)

            now = datetime.now(timezone.utc)
            stale_lz.payment_method = "closed"
            stale_lz.paid_at = now
            stale_lz.payment_notes = (
                f"Automatisch übertragen auf Laufzettel #{today_lz.id} ({today})"
            )

            logger.info(
                "Closed stale laufzettel id=%s (date=%s) → carried to id=%s",
                stale_lz.id,
                stale_lz.date,
                today_lz.id,
            )
            results.append(
                {
                    "action": "carried_over",
                    "closed_laufzettel_id": stale_lz.id,
                    "new_laufzettel_id": today_lz.id,
                }
            )

    db.commit()

    if today_lz is not None:
        db.refresh(today_lz)

    if not results:
        return {"action": "none"}

    actions = {r["action"] for r in results}
    if "carried_over" in actions:
        return {
            "action": "carried_over",
            "new_laufzettel": today_lz,
            "results": results,
        }
    return {"action": "deleted", "results": results}


# ── Device Session / Time Tracking helpers ──────────────────────────────────


def calculate_session_price(
    duration_seconds: int, pricing_model: str, unit_price: float
) -> tuple[float, float, str]:
    """Calculate price for a device session based on duration and pricing model.

    Returns (calculated_price, menge, unit).
    """
    if pricing_model == "per_hour":
        hours = duration_seconds / 3600.0
        price = round(hours * unit_price, 2)
        return price, round(hours, 2), "h"
    else:
        # Default to per_minute (covers "per_minute" and any unknown model)
        minutes = duration_seconds / 60.0
        price = round(minutes * unit_price, 2)
        return price, round(minutes, 2), "min"


def end_device_session(
    db: Session,
    session: "DeviceSession",
    ended_by: str = "scan",
    end_time: datetime | None = None,
) -> dict:
    """End a device session: compute duration, price, and create/update LaufzettelMaterial.

    Returns a dict with the session result.
    """
    from .models import Laufzettel

    if end_time is None:
        end_time = datetime.now(timezone.utc)

    # Ensure start_time is timezone-aware
    start = session.start_time
    if start and start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    duration_seconds = int((end_time - start).total_seconds())
    if duration_seconds < 0:
        duration_seconds = 0

    # Look up variante for pricing details
    unit_price = 0.0
    pricing_model = "per_minute"
    variante_name = "Gerätenutzung"
    try:
        from backend.catalog.db import SessionLocal as CatalogSession
        from backend.catalog.models import MaterialVariante

        cat_db = CatalogSession()
        try:
            variante = (
                cat_db.query(MaterialVariante)
                .filter(MaterialVariante.id == session.variante_id)
                .first()
            )
            if variante:
                unit_price = variante.price or 0.0
                pricing_model = variante.pricing_model or "per_minute"
                variante_name = variante.name or "Gerätenutzung"
        finally:
            cat_db.close()
    except Exception:
        logger.exception(
            "[DEVICE_SESSION] Failed to look up variante for session %s", session.id
        )

    calculated_price, menge, unit = calculate_session_price(
        duration_seconds, pricing_model, unit_price
    )

    session.end_time = end_time
    session.duration_seconds = duration_seconds
    session.calculated_price = calculated_price
    session.is_active = 0
    session.ended_by = ended_by

    # Create/update LaufzettelMaterial
    lz = db.query(Laufzettel).filter(Laufzettel.id == session.laufzettel_id).first()
    if lz and not lz.payment_method:
        material_name = f"{variante_name} (Zeit)"
        existing_mat = (
            db.query(LaufzettelMaterial)
            .filter(
                LaufzettelMaterial.laufzettel_id == lz.id,
                LaufzettelMaterial.name == material_name,
                LaufzettelMaterial.variante_id == session.variante_id,
            )
            .first()
        )
        if existing_mat:
            existing_mat.menge = round(
                (existing_mat.menge or 0) + menge, 2
            )
            existing_mat.calculated_price = round(
                (existing_mat.calculated_price or 0) + calculated_price, 2
            )
        else:
            new_mat = LaufzettelMaterial(
                laufzettel_id=lz.id,
                name=material_name,
                menge=menge,
                unit=unit,
                variante_id=session.variante_id,
                calculated_price=calculated_price,
                tax_rate=session.tax_rate,
            )
            db.add(new_mat)

    db.commit()
    db.refresh(session)

    logger.info(
        "[DEVICE_SESSION] Ended session %s: device=%s duration=%ds price=%.2f ended_by=%s",
        session.id,
        session.device_id,
        duration_seconds,
        calculated_price,
        ended_by,
    )

    return {
        "session_id": session.id,
        "duration_seconds": duration_seconds,
        "calculated_price": calculated_price,
        "ended_by": ended_by,
    }


def auto_end_sessions_at_2100():
    """Auto-logout all active device sessions at 21:00 local time (Europe/Berlin).

    Called by APScheduler cron job.
    """
    from .db import SessionLocal

    db = SessionLocal()
    ended_count = 0
    try:
        from datetime import datetime as dt_datetime
        from zoneinfo import ZoneInfo

        berlin = ZoneInfo("Europe/Berlin")
        now_berlin = dt_datetime.now(berlin)
        # Use 21:00 Berlin time, or now if already past
        cutoff = now_berlin.replace(hour=21, minute=0, second=0, microsecond=0)
        end_time_utc = cutoff.astimezone(timezone.utc)

        active_sessions = (
            db.query(DeviceSession).filter(DeviceSession.is_active == 1).all()
        )

        for session in active_sessions:
            try:
                end_device_session(
                    db, session, ended_by="auto_2100", end_time=end_time_utc
                )
                ended_count += 1
            except Exception:
                logger.exception("[AUTO_2100] Failed to end session %s", session.id)

        db.commit()
        logger.info("[AUTO_2100] Auto-ended %d active device sessions", ended_count)
    except Exception:
        logger.exception("[AUTO_2100] Failed")
        db.rollback()
    finally:
        db.close()

    return ended_count

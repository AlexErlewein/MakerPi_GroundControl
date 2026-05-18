"""Utility functions for laufzettel lifecycle management."""

import logging
from datetime import datetime, date, timezone
from sqlalchemy.orm import Session

from .models import Laufzettel, LaufzettelMaterial

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
                "Deleting empty stale laufzettel id=%s (date=%s) for mitglied_id=%s",
                stale_lz.id,
                stale_lz.date,
                mitglied_id,
            )
            db.delete(stale_lz)
            results.append({"action": "deleted", "laufzettel_id": stale_lz.id})
        else:
            # Ensure we have a today-laufzettel to carry into
            if today_lz is None:
                today_lz = (
                    db.query(Laufzettel)
                    .filter(
                        Laufzettel.mitglied_id == mitglied_id,
                        Laufzettel.payment_method.is_(None),
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

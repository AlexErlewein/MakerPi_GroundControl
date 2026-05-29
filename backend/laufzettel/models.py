"""Laufzettel models - work orders and material entries"""

import json
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, Date, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


def _naive_to_utc(dt):
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class Laufzettel(Base):
    __tablename__ = "laufzettel"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, index=True)
    date = Column(Date, index=True)
    start = Column(DateTime(timezone=True), nullable=True)
    owner_name = Column(String, nullable=True)
    member_id = Column(String, nullable=True)
    mitglied_id = Column(
        Integer, nullable=True, index=True
    )  # soft ref to members.mitglieder.id
    guest_id = Column(String, nullable=True, index=True)  # UUID for guest sessions
    guest_email = Column(String, nullable=True)  # Optional email for guests
    nodes = Column(Text, default="[]")  # JSON array of device_ids
    payment_method = Column(
        String, nullable=True
    )  # 'bar' | 'paypal' | 'karte' | 'wero'
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_transaction_id = Column(String, nullable=True)  # SumUp transaction ID
    payment_notes = Column(
        String, nullable=True
    )  # free-text note (e.g. for cash payments)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self):
        start_ts = _naive_to_utc(self.start) if self.start else None
        paid_ts = _naive_to_utc(self.paid_at) if self.paid_at else None
        return {
            "id": self.id,
            "uid": self.uid,
            "date": self.date.isoformat() if self.date else None,
            "start": start_ts.isoformat() if start_ts else None,
            "owner_name": self.owner_name,
            "member_id": self.member_id,
            "mitglied_id": self.mitglied_id,
            "guest_id": self.guest_id,
            "guest_email": self.guest_email,
            "nodes": json.loads(self.nodes) if self.nodes else [],
            "payment_method": self.payment_method,
            "paid_at": paid_ts.isoformat() if paid_ts else None,
            "payment_transaction_id": self.payment_transaction_id,
            "payment_notes": self.payment_notes,
            "created_at": _naive_to_utc(self.created_at).isoformat()
            if self.created_at
            else None,
        }


class LaufzettelMaterial(Base):
    __tablename__ = "laufzettel_material"

    id = Column(Integer, primary_key=True, index=True)
    laufzettel_id = Column(Integer, index=True)
    name = Column(String)
    menge = Column(Float, nullable=True)
    # Catalog link (optional) - soft ref to catalog.MaterialVariante
    variante_id = Column(Integer, nullable=True, index=True)
    unit = Column(String, nullable=True)
    # Dimensions for per_volume_cm3 pricing
    laenge_cm = Column(Float, nullable=True)
    breite_cm = Column(Float, nullable=True)
    hoehe_cm = Column(Float, nullable=True)
    calculated_price = Column(Float, nullable=True)
    tax_rate = Column(
        Float, nullable=True
    )  # snapshotted from MaterialKategorie; None treated as 19.0
    is_spende = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "laufzettel_id": self.laufzettel_id,
            "name": self.name,
            "menge": self.menge,
            "variante_id": self.variante_id,
            "unit": self.unit,
            "laenge_cm": self.laenge_cm,
            "breite_cm": self.breite_cm,
            "hoehe_cm": self.hoehe_cm,
            "calculated_price": self.calculated_price,
            "tax_rate": 0.0
            if self.tax_rate is not None and self.tax_rate == 0
            else self.tax_rate,
            "is_spende": bool(self.is_spende) if self.is_spende is not None else False,
        }


class LaufzettelGutschein(Base):
    __tablename__ = "laufzettel_gutschein"

    id = Column(Integer, primary_key=True, index=True)
    laufzettel_id = Column(Integer, index=True)
    shopify_gift_card_id = Column(String)  # Shopify numeric ID as string
    last_chars = Column(String)  # last 4 chars of the GC code for display
    amount_debited = Column(Float)  # EUR amount taken from the card
    transaction_id = Column(String, nullable=True)  # Shopify transaction GID
    applied_at = Column(DateTime(timezone=True), default=_utcnow)
    applied_by = Column(String, nullable=True)  # username or "member"
    note = Column(String, nullable=True)

    def to_dict(self):
        applied_ts = _naive_to_utc(self.applied_at) if self.applied_at else None
        return {
            "id": self.id,
            "laufzettel_id": self.laufzettel_id,
            "shopify_gift_card_id": self.shopify_gift_card_id,
            "last_chars": self.last_chars,
            "amount_debited": self.amount_debited,
            "transaction_id": self.transaction_id,
            "applied_at": applied_ts.isoformat() if applied_ts else None,
            "applied_by": self.applied_by,
            "note": self.note,
        }

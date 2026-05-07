from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


class Verkauf(Base):
    __tablename__ = "verkauf"
    id = Column(Integer, primary_key=True)
    laufzettel_id = Column(Integer, index=True, nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=False)
    payment_method = Column(String, nullable=False)
    variante_id = Column(Integer, nullable=True, index=True)
    variante_name = Column(String, nullable=False)
    kategorie_name = Column(String, nullable=True)
    pricing_model = Column(String, nullable=True)
    menge = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    calculated_price = Column(Float, nullable=False)
    tax_rate = Column(Float, nullable=True)
    member_id = Column(String, nullable=True)
    owner_name = Column(String, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "laufzettel_id": self.laufzettel_id,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "payment_method": self.payment_method,
            "variante_id": self.variante_id,
            "variante_name": self.variante_name,
            "kategorie_name": self.kategorie_name,
            "pricing_model": self.pricing_model,
            "menge": self.menge,
            "unit": self.unit,
            "calculated_price": self.calculated_price,
            "tax_rate": self.tax_rate,
            "member_id": self.member_id,
            "owner_name": self.owner_name,
        }


class Spende(Base):
    __tablename__ = "spende"
    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    donor_name = Column(String, nullable=True)
    date = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "donor_name": self.donor_name,
            "date": self.date.isoformat() if self.date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

"""Members models - Mitglied and RFIDTag tables"""

from datetime import datetime, timezone, date as date_type
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


def _naive_to_utc(dt):
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class Mitglied(Base):
    __tablename__ = "mitglieder"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    status = Column(String, default="active")  # active | inactive
    joined_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    # Login credentials (optional - for cardless login)
    nfc_uid = Column(
        String, unique=True, nullable=True, index=True
    )  # Primary NFC card UID
    login_username = Column(String, unique=True, nullable=True, index=True)
    login_password_hash = Column(String, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "member_id": self.member_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
            "joined_date": self.joined_date.isoformat() if self.joined_date else None,
            "notes": self.notes,
            "nfc_uid": self.nfc_uid,
            "login_username": self.login_username,
            "has_login": bool(self.login_username and self.login_password_hash),
        }


class RFIDTag(Base):
    __tablename__ = "rfid_tags"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, unique=True, index=True)
    member_id = Column(String, nullable=True, index=True)  # soft ref to Mitglied
    owner_name = Column(String)
    owner_email = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    active = Column(Integer, default=1)  # 1=active, 0=disabled
    is_admin = Column(Boolean, default=False)  # Admin card?
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self):
        ts = _naive_to_utc(self.created_at) if self.created_at else None
        return {
            "id": self.id,
            "uid": self.uid,
            "member_id": self.member_id,
            "owner_name": self.owner_name,
            "owner_email": self.owner_email,
            "notes": self.notes,
            "active": bool(self.active),
            "is_admin": bool(self.is_admin),
            "created_at": ts.isoformat() if ts else None,
        }

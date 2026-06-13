"""Core models - MQTT messages, devices, and tag scans"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


def _naive_to_utc(dt):
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class MQTTMessage(Base):
    __tablename__ = "mqtt_messages"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    payload = Column(Text)
    qos = Column(Integer)
    retained = Column(Integer, default=0)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self):
        ts = _naive_to_utc(self.timestamp) if self.timestamp else None
        return {
            "id": self.id,
            "topic": self.topic,
            "payload": self.payload,
            "qos": self.qos,
            "retained": bool(self.retained),
            "timestamp": ts.isoformat() if ts else None,
        }


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True)
    name = Column(String)
    last_seen = Column(DateTime(timezone=True), default=_utcnow)
    status = Column(String, default="unknown")
    nfc_ok = Column(Integer, default=None)  # NULL = unknown, 1 = OK, 0 = error
    nfc_error = Column(String, default=None)
    requires_permission = Column(
        Integer, default=1
    )  # 1 = requires permission (default), 0 = no permission required

    def to_dict(self):
        ts = _naive_to_utc(self.last_seen) if self.last_seen else None
        return {
            "id": self.id,
            "device_id": self.device_id,
            "name": self.name,
            "last_seen": ts.isoformat() if ts else None,
            "status": self.status,
            "nfc_ok": self.nfc_ok,
            "nfc_error": self.nfc_error,
            "requires_permission": bool(self.requires_permission)
            if self.requires_permission is not None
            else True,
        }


class TagScan(Base):
    __tablename__ = "tag_scans"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, index=True)
    device_id = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)
    validated = Column(Integer, default=0)  # 1=known tag, 0=unknown
    owner_name = Column(String, nullable=True)
    tag_type = Column(String, nullable=True)
    atqa = Column(String, nullable=True)
    sak = Column(String, nullable=True)
    card_member_id = Column(String, nullable=True)
    card_name = Column(String, nullable=True)
    card_email = Column(String, nullable=True)
    card_signature = Column(String, nullable=True)
    # 3VL: None=legacy (no sig data), 1=HMAC verified, 0=HMAC rejected (clone attempt)
    card_verified = Column(Integer, nullable=True)

    def to_dict(self):
        ts = _naive_to_utc(self.timestamp) if self.timestamp else None
        return {
            "id": self.id,
            "uid": self.uid,
            "device_id": self.device_id,
            "timestamp": ts.isoformat() if ts else None,
            "validated": bool(self.validated),
            "owner_name": self.owner_name,
            "tag_type": self.tag_type,
            "atqa": self.atqa,
            "sak": self.sak,
            "card_member_id": self.card_member_id,
            "card_name": self.card_name,
            "card_email": self.card_email,
            "card_signature": self.card_signature,
            "card_verified": self.card_verified,
        }


class DevicePairing(Base):
    """Token-based pairing between NFC scanner and client device."""

    __tablename__ = "device_pairings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        String, index=True
    )  # NFC scanner device ID (e.g., "picow_nfc_01")
    token_hash = Column(String, index=True)  # SHA256 hash of the pairing token
    paired_by = Column(String)  # Username of admin who created the pairing
    paired_at = Column(DateTime(timezone=True), default=_utcnow)
    last_used = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    description = Column(
        String, nullable=True
    )  # Human-readable description (e.g., "Kasse Tablet 1")
    client_ip = Column(String, nullable=True)  # IP of client when last used

    def to_dict(self):
        paired_at_ts = _naive_to_utc(self.paired_at) if self.paired_at else None
        last_used_ts = _naive_to_utc(self.last_used) if self.last_used else None
        expires_at_ts = _naive_to_utc(self.expires_at) if self.expires_at else None
        return {
            "id": self.id,
            "device_id": self.device_id,
            "paired_by": self.paired_by,
            "paired_at": paired_at_ts.isoformat() if paired_at_ts else None,
            "last_used": last_used_ts.isoformat() if last_used_ts else None,
            "expires_at": expires_at_ts.isoformat() if expires_at_ts else None,
            "description": self.description,
            "client_ip": self.client_ip,
        }

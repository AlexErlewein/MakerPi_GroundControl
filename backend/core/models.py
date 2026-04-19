"""Core models - MQTT messages, devices, and tag scans"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
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
        }

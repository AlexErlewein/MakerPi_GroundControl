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


class ZigbeeDevice(Base):
    __tablename__ = "zigbee_devices"

    id = Column(Integer, primary_key=True, index=True)
    ieee_address = Column(String, unique=True, index=True)  # 0x00158d00044c2287
    friendly_name = Column(String)  # z.B. "temperatur_sensor_buero"
    last_seen = Column(DateTime(timezone=True), default=_utcnow)
    status = Column(String, default="unknown")  # online, offline, unknown
    battery = Column(Integer, nullable=True)  # Battery level in %
    linkquality = Column(Integer, nullable=True)  # Signal quality
    model = Column(String, nullable=True)  # z.B. "WSDCGQ11LM"
    vendor = Column(String, nullable=True)  # z.B. "Xiaomi"
    description = Column(String, nullable=True)  # z.B. "Aqara temperature sensor"
    exposes = Column(Text, nullable=True)  # JSON array of exposed capabilities
    raw_payload = Column(Text, nullable=True)  # Last payload as JSON

    def to_dict(self):
        ts = _naive_to_utc(self.last_seen) if self.last_seen else None
        return {
            "id": self.id,
            "ieee_address": self.ieee_address,
            "friendly_name": self.friendly_name,
            "last_seen": ts.isoformat() if ts else None,
            "status": self.status,
            "battery": self.battery,
            "linkquality": self.linkquality,
            "model": self.model,
            "vendor": self.vendor,
            "description": self.description,
            "exposes": self.exposes,
            "raw_payload": self.raw_payload,
        }

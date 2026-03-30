"""
MakerPi GroundControl - Main FastAPI Application
MQTT Broker integration with SQLite database and Web UI
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone, date as date_type
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, Text, UniqueConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
DATABASE_URL = "sqlite:///./groundcontrol.db"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _utcnow():
    """Get current UTC time as timezone-aware datetime"""
    return datetime.now(timezone.utc)


def _naive_to_utc(dt):
    """Convert naive datetime to UTC-aware datetime"""
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


class RFIDTag(Base):
    __tablename__ = "rfid_tags"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, unique=True, index=True)
    member_id = Column(String, nullable=True, index=True)
    owner_name = Column(String)
    owner_email = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    active = Column(Integer, default=1)  # 1=active, 0=disabled
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
            "created_at": ts.isoformat() if ts else None,
        }


class Laufzettel(Base):
    __tablename__ = "laufzettel"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, index=True)
    date = Column(Date, index=True)
    start = Column(DateTime(timezone=True), nullable=True)
    owner_name = Column(String, nullable=True)
    member_id = Column(String, nullable=True)
    nodes = Column(Text, default="[]")  # JSON array of device_ids

    __table_args__ = (UniqueConstraint("uid", "date", name="uq_laufzettel_uid_date"),)

    def to_dict(self):
        start_ts = _naive_to_utc(self.start) if self.start else None
        return {
            "id": self.id,
            "uid": self.uid,
            "date": self.date.isoformat() if self.date else None,
            "start": start_ts.isoformat() if start_ts else None,
            "owner_name": self.owner_name,
            "member_id": self.member_id,
            "nodes": json.loads(self.nodes) if self.nodes else [],
        }


class LaufzettelMaterial(Base):
    __tablename__ = "laufzettel_material"

    id = Column(Integer, primary_key=True, index=True)
    laufzettel_id = Column(Integer, index=True)
    name = Column(String)
    menge = Column(Float, nullable=True)
    # Catalog link (optional)
    variante_id = Column(Integer, nullable=True, index=True)
    unit = Column(String, nullable=True)
    # Dimensions for per_volume_cm3 pricing
    laenge_cm = Column(Float, nullable=True)
    breite_cm = Column(Float, nullable=True)
    hoehe_cm = Column(Float, nullable=True)
    calculated_price = Column(Float, nullable=True)

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
        }


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class MaterialKategorie(Base):
    __tablename__ = "material_kategorie"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, index=True)
    name = Column(String)
    pricing_model = Column(String, default="per_unit")  # per_gram | per_volume_cm3 | per_unit
    unit = Column(String, nullable=True)  # display unit e.g. 'g', 'cm³', 'Stück'

    def to_dict(self):
        return {
            "id": self.id,
            "location_id": self.location_id,
            "name": self.name,
            "pricing_model": self.pricing_model,
            "unit": self.unit,
        }


class MaterialVariante(Base):
    __tablename__ = "material_variante"

    id = Column(Integer, primary_key=True, index=True)
    kategorie_id = Column(Integer, index=True)
    name = Column(String)
    price = Column(Float)  # price per gram / per cm³ / per unit

    def to_dict(self):
        return {
            "id": self.id,
            "kategorie_id": self.kategorie_id,
            "name": self.name,
            "price": self.price,
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


# Create tables
Base.metadata.create_all(bind=engine)

# Migrate existing tables: add new columns if they don't exist
def _run_migrations():
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(
            text("PRAGMA table_info(laufzettel_material)")
        )}
        new_cols = {
            "variante_id": "INTEGER",
            "unit": "VARCHAR",
            "laenge_cm": "FLOAT",
            "breite_cm": "FLOAT",
            "hoehe_cm": "FLOAT",
            "calculated_price": "FLOAT",
        }
        for col, col_type in new_cols.items():
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE laufzettel_material ADD COLUMN {col} {col_type}"
                ))
        conn.commit()

_run_migrations()

# Global MQTT client
mqtt_client = None


class MQTTHandler:
    """Handles MQTT connection and message processing"""

    def __init__(self, broker: str, port: int):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.connected = False

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Called when MQTT client connects to broker"""
        if reason_code == 0:
            logger.info(f"Connected to MQTT broker {self.broker}:{self.port}")
            self.connected = True
            # Subscribe to all topics
            client.subscribe("#")
        else:
            logger.error(f"Failed to connect to MQTT broker: {reason_code}")

    def on_disconnect(self, client, userdata, reason_code, properties):
        """Called when MQTT client disconnects"""
        logger.warning(f"Disconnected from MQTT broker: {reason_code}")
        self.connected = False

    def on_message(self, client, userdata, msg):
        """Called when MQTT message is received"""
        try:
            payload = msg.payload.decode("utf-8")
            logger.info(f"Received: {msg.topic} -> {payload}")

            # Store in database
            db = SessionLocal()
            try:
                mqtt_message = MQTTMessage(
                    topic=msg.topic,
                    payload=payload,
                    qos=msg.qos,
                    retained=msg.retain,
                )
                db.add(mqtt_message)

                # Update device if this looks like a device message
                topic_parts = msg.topic.split("/")
                if len(topic_parts) > 0:
                    device_id = topic_parts[0]
                    device = (
                        db.query(Device).filter(Device.device_id == device_id).first()
                    )

                    # Handle heartbeat messages (extract NFC status)
                    if len(topic_parts) > 1 and topic_parts[1] == "heartbeat":
                        try:
                            heartbeat_data = json.loads(payload)
                            if device:
                                device.last_seen = _utcnow()
                                # Update NFC status from heartbeat
                                device.nfc_ok = 1 if heartbeat_data.get("nfc_ok") else 0
                                device.nfc_error = heartbeat_data.get("nfc_error")
                                device.status = heartbeat_data.get("status", "online")
                            else:
                                # Create new device from heartbeat
                                device = Device(
                                    device_id=device_id,
                                    name=device_id,
                                    status=heartbeat_data.get("status", "online"),
                                    nfc_ok=1 if heartbeat_data.get("nfc_ok") else 0,
                                    nfc_error=heartbeat_data.get("nfc_error"),
                                )
                                db.add(device)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid heartbeat JSON from {device_id}")

                    # Handle status messages
                    elif len(topic_parts) > 1 and topic_parts[1] == "status":
                        try:
                            status_data = json.loads(payload)
                            if device:
                                device.last_seen = _utcnow()
                                device.status = status_data.get("status", "unknown")
                            else:
                                device = Device(
                                    device_id=device_id,
                                    name=device_id,
                                    status=status_data.get("status", "unknown"),
                                )
                                db.add(device)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid status JSON from {device_id}")

                    # Handle NFC tag scan messages
                    elif len(topic_parts) > 1 and topic_parts[1] in ("nfc", "tag"):
                        try:
                            tag_data = json.loads(payload)
                            uid = tag_data.get("uid", "").upper()
                            if uid:
                                known = db.query(RFIDTag).filter(
                                    RFIDTag.uid == uid, RFIDTag.active == 1
                                ).first()
                                scan = TagScan(
                                    uid=uid,
                                    device_id=device_id,
                                    validated=1 if known else 0,
                                    owner_name=known.owner_name if known else None,
                                    tag_type=tag_data.get("tag_type"),
                                    atqa=tag_data.get("atqa"),
                                    sak=tag_data.get("sak"),
                                )
                                db.add(scan)
                                logger.info(
                                    f"Tag scan: {uid} from {device_id} - "
                                    f"{'VALID: ' + known.owner_name if known else 'UNKNOWN'}"
                                )
                                # Upsert Laufzettel for known tags
                                if known:
                                    today = date_type.today()
                                    now = _utcnow()
                                    lz = db.query(Laufzettel).filter(
                                        Laufzettel.uid == uid,
                                        Laufzettel.date == today,
                                    ).first()
                                    if lz is None:
                                        lz = Laufzettel(
                                            uid=uid,
                                            date=today,
                                            start=now,
                                            owner_name=known.owner_name,
                                            member_id=known.member_id,
                                            nodes=json.dumps([device_id]),
                                        )
                                        db.add(lz)
                                        logger.info(f"Laufzettel created for {uid} on {today}")
                                    else:
                                        nodes = json.loads(lz.nodes) if lz.nodes else []
                                        if device_id not in nodes:
                                            nodes.append(device_id)
                                            lz.nodes = json.dumps(nodes)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid NFC JSON from {device_id}")
                        else:
                            if uid:
                                self.publish_user_info(
                                    uid=uid,
                                    owner_name=known.owner_name if known else None,
                                    validated=bool(known),
                                    tag_type=tag_data.get("tag_type"),
                                )

                    # Handle material messages
                    elif len(topic_parts) > 1 and topic_parts[1] == "material":
                        try:
                            mat_data = json.loads(payload)
                            uid = mat_data.get("uid", "").upper()
                            mat_name = mat_data.get("name", "")
                            mat_menge = mat_data.get("menge")
                            if uid and mat_name and mat_menge is not None:
                                today = date_type.today()
                                lz = db.query(Laufzettel).filter(
                                    Laufzettel.uid == uid,
                                    Laufzettel.date == today,
                                ).first()
                                if lz:
                                    mat = LaufzettelMaterial(
                                        laufzettel_id=lz.id,
                                        name=mat_name,
                                        menge=float(mat_menge),
                                    )
                                    db.add(mat)
                                    logger.info(f"Material added to Laufzettel {lz.id}: {mat_name} {mat_menge}")
                                else:
                                    logger.warning(f"No Laufzettel for {uid} today, material ignored")
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid material JSON from {device_id}")

                    # Generic device update (any message from device)
                    elif device:
                        device.last_seen = _utcnow()
                        device.status = "online"
                    else:
                        # Create new device from generic message
                        device = Device(
                            device_id=device_id, name=device_id, status="online"
                        )
                        db.add(device)

                db.commit()
            except Exception as e:
                logger.error(f"Database error: {e}")
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def start(self):
        """Connect to MQTT broker and start loop"""
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")

    def stop(self):
        """Stop MQTT client"""
        self.client.loop_stop()
        self.client.disconnect()

    def publish_user_info(
        self,
        uid: str,
        owner_name: str | None,
        validated: bool,
        tag_type: str | None,
    ):
        """Publish NFC scan result to the display topic"""
        payload = json.dumps({
            "uid": uid,
            "owner_name": owner_name,
            "validated": validated,
            "tag_type": tag_type,
        })
        try:
            self.client.publish("lilygo/user_info", payload.encode("utf-8"), qos=1)
            logger.info(f"Published user info for {uid} (validated={validated})")
        except Exception as e:
            logger.error(f"Failed to publish user info: {e}")

    def publish_command(self, device_id: str, command: str, payload: str = ""):
        """Publish a command to a device via MQTT"""
        topic = f"{device_id}/command"
        # Use command as payload if no explicit payload provided
        payload_to_send = payload if payload else command
        try:
            result = self.client.publish(topic, payload_to_send.encode("utf-8"), qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Command sent: {topic} -> {payload_to_send}")
                return True
            else:
                logger.error(f"Failed to send command: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False


# Lifespan manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global mqtt_client

    # Startup
    logger.info("Starting GroundControl...")
    mqtt_client = MQTTHandler(MQTT_BROKER, MQTT_PORT)
    mqtt_client.start()

    # Give MQTT time to connect
    await asyncio.sleep(1)

    yield

    # Shutdown
    logger.info("Shutting down GroundControl...")
    if mqtt_client:
        mqtt_client.stop()


# FastAPI app
app = FastAPI(
    title="MakerPi GroundControl",
    description="MQTT Broker management and monitoring",
    version="0.1.0",
    lifespan=lifespan,
)

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# API Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Render main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def get_status():
    """Get system status"""
    return {
        "mqtt_connected": mqtt_client.connected if mqtt_client else False,
        "broker": f"{MQTT_BROKER}:{MQTT_PORT}",
        "timestamp": _utcnow().isoformat(),
    }


@app.get("/api/devices")
async def get_devices():
    """Get all registered devices"""
    db: Session = SessionLocal()
    try:
        devices = db.query(Device).all()
        return [d.to_dict() for d in devices]
    finally:
        db.close()


@app.get("/api/messages")
async def get_messages(limit: int = 100, topic: str = None):
    """Get recent MQTT messages"""
    db: Session = SessionLocal()
    try:
        query = db.query(MQTTMessage)
        if topic:
            query = query.filter(MQTTMessage.topic.like(f"{topic}%"))
        messages = query.order_by(MQTTMessage.timestamp.desc()).limit(limit).all()
        return [m.to_dict() for m in messages]
    finally:
        db.close()


@app.get("/api/topics")
async def get_topics():
    """Get list of all topics"""
    db: Session = SessionLocal()
    try:
        topics = db.query(MQTTMessage.topic).distinct().all()
        return [t[0] for t in topics]
    finally:
        db.close()


@app.get("/api/database/stats")
async def get_database_stats():
    """Get database statistics"""
    from sqlalchemy import func
    import os

    db: Session = SessionLocal()
    try:
        # Count records
        device_count = db.query(Device).count()
        message_count = db.query(MQTTMessage).count()
        topic_count = db.query(MQTTMessage.topic).distinct().count()

        # Online devices
        online_count = db.query(Device).filter(Device.status == "online").count()

        # NFC status counts
        nfc_ok = db.query(Device).filter(Device.nfc_ok == 1).count()
        nfc_error = db.query(Device).filter(Device.nfc_ok == 0).count()
        nfc_unknown = db.query(Device).filter(Device.nfc_ok.is_(None)).count()

        # Timestamp ranges
        oldest_message = db.query(func.min(MQTTMessage.timestamp)).scalar()
        newest_message = db.query(func.max(MQTTMessage.timestamp)).scalar()
        oldest_device = db.query(func.min(Device.last_seen)).scalar()
        newest_device = db.query(func.max(Device.last_seen)).scalar()

        # Database file size
        db_path = Path("groundcontrol.db")
        db_size = db_path.stat().st_size if db_path.exists() else 0

        return {
            "devices": {
                "total": device_count,
                "online": online_count,
                "offline": device_count - online_count,
                "nfc_ok": nfc_ok,
                "nfc_error": nfc_error,
                "nfc_unknown": nfc_unknown,
            },
            "messages": {
                "total": message_count,
                "topics": topic_count,
                "oldest": oldest_message.isoformat() if oldest_message else None,
                "newest": newest_message.isoformat() if newest_message else None,
            },
            "database": {
                "size_bytes": db_size,
                "size_human": _human_readable_size(db_size),
                "file_path": str(db_path),
            },
            "devices_oldest_seen": oldest_device.isoformat() if oldest_device else None,
            "devices_newest_seen": newest_device.isoformat() if newest_device else None,
        }
    finally:
        db.close()


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human readable format"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


@app.get("/api/devices/{device_id}")
async def get_device_detail(device_id: str):
    """Get detailed information about a specific device"""
    db: Session = SessionLocal()
    try:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            return JSONResponse(status_code=404, content={"detail": "Device not found"})

        # Get recent messages for this device
        messages = (
            db.query(MQTTMessage)
            .filter(MQTTMessage.topic.like(f"{device_id}/%"))
            .order_by(MQTTMessage.timestamp.desc())
            .limit(100)
            .all()
        )

        # Get message count per topic
        from sqlalchemy import func

        topic_counts = (
            db.query(MQTTMessage.topic, func.count(MQTTMessage.id))
            .filter(MQTTMessage.topic.like(f"{device_id}/%"))
            .group_by(MQTTMessage.topic)
            .all()
        )

        return {
            "device": device.to_dict(),
            "recent_messages": [m.to_dict() for m in messages],
            "topic_counts": [{"topic": t[0], "count": t[1]} for t in topic_counts],
        }
    except Exception as e:
        logger.error(f"Error fetching device {device_id}: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.get("/api/devices/{device_id}/messages")
async def get_device_messages(device_id: str, limit: int = 100, topic: str = None):
    """Get messages for a specific device"""
    db: Session = SessionLocal()
    try:
        query = db.query(MQTTMessage).filter(MQTTMessage.topic.like(f"{device_id}/%"))
        if topic:
            query = query.filter(MQTTMessage.topic.like(f"{device_id}/{topic}%"))
        messages = query.order_by(MQTTMessage.timestamp.desc()).limit(limit).all()
        return [m.to_dict() for m in messages]
    finally:
        db.close()


@app.post("/api/devices/{device_id}/commands")
async def send_device_command(device_id: str, command: str = Query(..., description="Command to send to device")):
    """Send a command to a device via MQTT"""
    if not mqtt_client:
        return JSONResponse(status_code=503, content={"success": False, "error": "MQTT not connected"})

    if not mqtt_client.connected:
        return JSONResponse(status_code=503, content={"success": False, "error": "MQTT not connected"})

    success = mqtt_client.publish_command(device_id, command)
    return {"success": success, "command": command, "device_id": device_id}


@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str):
    """Delete a device from the database"""
    db: Session = SessionLocal()
    try:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            return JSONResponse(status_code=404, content={"detail": "Device not found"})

        db.delete(device)
        db.commit()
        logger.info(f"Device deleted: {device_id}")
        return {"success": True, "message": f"Device '{device_id}' deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting device {device_id}: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.get("/api/export/devices")
async def export_devices():
    """Export all devices as CSV"""
    import csv
    from fastapi.responses import Response

    db: Session = SessionLocal()
    try:
        devices = db.query(Device).all()

        output = []
        output.append("device_id,name,status,last_seen,nfc_ok,nfc_error")

        for device in devices:
            nfc_status = (
                "OK"
                if device.nfc_ok == 1
                else "Error"
                if device.nfc_ok == 0
                else "Unknown"
            )
            output.append(
                f'"{device.device_id}","{device.name}","{device.status}",'
                f'"{device.last_seen.isoformat() if device.last_seen else ""}",'
                f'"{nfc_status}","{device.nfc_error or ""}"'
            )

        csv_content = "\n".join(output)

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=devices.csv"},
        )
    finally:
        db.close()


@app.get("/api/export/messages")
async def export_messages(limit: int = 1000):
    """Export messages as CSV"""
    from fastapi.responses import Response

    db: Session = SessionLocal()
    try:
        messages = (
            db.query(MQTTMessage)
            .order_by(MQTTMessage.timestamp.desc())
            .limit(limit)
            .all()
        )

        output = []
        output.append("id,topic,payload,qos,retained,timestamp")

        for msg in messages:
            escaped_payload = msg.payload.replace('"', '""') if msg.payload else ""
            output.append(
                f'{msg.id},"{msg.topic}","{escaped_payload}",'
                f"{msg.qos},{msg.retained},"
                f'"{msg.timestamp.isoformat() if msg.timestamp else ""}"'
            )

        csv_content = "\n".join(output)

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=messages_{limit}.csv"
            },
        )
    finally:
        db.close()


class TagCreate(BaseModel):
    uid: str
    owner_name: str
    member_id: str = None
    owner_email: str = None
    notes: str = None
    active: bool = True


class TagUpdate(BaseModel):
    owner_name: str = None
    member_id: str = None
    owner_email: str = None
    notes: str = None
    active: bool = None


class LaufzettelCreate(BaseModel):
    uid: str
    date: str = None  # ISO date string, defaults to today
    owner_name: str = None
    member_id: str = None
    start: str = None  # ISO datetime string


class LaufzettelUpdate(BaseModel):
    owner_name: str = None
    member_id: str = None
    start: str = None  # ISO datetime string


class MaterialCreate(BaseModel):
    name: str
    menge: float = None
    variante_id: int = None
    unit: str = None
    laenge_cm: float = None
    breite_cm: float = None
    hoehe_cm: float = None
    calculated_price: float = None


class MaterialUpdate(BaseModel):
    name: str = None
    menge: float = None
    variante_id: int = None
    unit: str = None
    laenge_cm: float = None
    breite_cm: float = None
    hoehe_cm: float = None
    calculated_price: float = None


class LocationCreate(BaseModel):
    name: str


class LocationUpdate(BaseModel):
    name: str = None


class KategorieCreate(BaseModel):
    location_id: int
    name: str
    pricing_model: str = "per_unit"
    unit: str = None


class KategorieUpdate(BaseModel):
    name: str = None
    pricing_model: str = None
    unit: str = None


class VarianteCreate(BaseModel):
    kategorie_id: int
    name: str
    price: float


class VarianteUpdate(BaseModel):
    name: str = None
    price: float = None


@app.get("/api/tags")
async def get_tags():
    """Get all registered RFID tags"""
    db: Session = SessionLocal()
    try:
        tags = db.query(RFIDTag).order_by(RFIDTag.owner_name).all()
        return [t.to_dict() for t in tags]
    finally:
        db.close()


@app.get("/api/tags/scans")
async def get_tag_scans(limit: int = 100):
    """Get recent tag scan events"""
    db: Session = SessionLocal()
    try:
        scans = db.query(TagScan).order_by(TagScan.timestamp.desc()).limit(limit).all()
        return [s.to_dict() for s in scans]
    finally:
        db.close()


@app.post("/api/tags")
async def create_tag(tag: TagCreate):
    """Register a new RFID tag"""
    db: Session = SessionLocal()
    try:
        uid = tag.uid.upper()
        existing = db.query(RFIDTag).filter(RFIDTag.uid == uid).first()
        if existing:
            return JSONResponse(status_code=400, content={"detail": f"Tag {uid} already registered"})
        new_tag = RFIDTag(
            uid=uid,
            owner_name=tag.owner_name,
            member_id=tag.member_id,
            owner_email=tag.owner_email,
            notes=tag.notes,
            active=1 if tag.active else 0,
        )
        db.add(new_tag)
        db.commit()
        db.refresh(new_tag)
        return new_tag.to_dict()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.put("/api/tags/{uid}")
async def update_tag(uid: str, tag: TagUpdate):
    """Update a registered RFID tag"""
    db: Session = SessionLocal()
    try:
        existing = db.query(RFIDTag).filter(RFIDTag.uid == uid.upper()).first()
        if not existing:
            return JSONResponse(status_code=404, content={"detail": "Tag not found"})
        if tag.owner_name is not None:
            existing.owner_name = tag.owner_name
        if tag.member_id is not None:
            existing.member_id = tag.member_id
        if tag.owner_email is not None:
            existing.owner_email = tag.owner_email
        if tag.notes is not None:
            existing.notes = tag.notes
        if tag.active is not None:
            existing.active = 1 if tag.active else 0
        db.commit()
        db.refresh(existing)
        return existing.to_dict()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.delete("/api/tags/{uid}")
async def delete_tag(uid: str):
    """Delete a registered RFID tag"""
    db: Session = SessionLocal()
    try:
        existing = db.query(RFIDTag).filter(RFIDTag.uid == uid.upper()).first()
        if not existing:
            return JSONResponse(status_code=404, content={"detail": "Tag not found"})
        db.delete(existing)
        db.commit()
        return {"success": True, "message": f"Tag {uid.upper()} deleted"}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.get("/tags", response_class=HTMLResponse)
async def tags_page(request: Request):
    """Render RFID tags management page"""
    return templates.TemplateResponse("tags.html", {"request": request})


@app.get("/database", response_class=HTMLResponse)
async def database_page(request: Request):
    """Render database overview page"""
    return templates.TemplateResponse("database.html", {"request": request})


@app.get("/devices/{device_id}", response_class=HTMLResponse)
async def device_detail_page(request: Request, device_id: str):
    """Render device detail page"""
    db: Session = SessionLocal()
    try:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return templates.TemplateResponse(
            "device-detail.html", {"request": request, "device_id": device_id}
        )
    finally:
        db.close()


@app.post("/api/laufzettel")
async def create_laufzettel(data: LaufzettelCreate):
    """Manually create a new Laufzettel entry"""
    db: Session = SessionLocal()
    try:
        uid = data.uid.upper()
        if data.date:
            try:
                from datetime import date as dt_date
                entry_date = dt_date.fromisoformat(data.date)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid date format, use YYYY-MM-DD"})
        else:
            entry_date = date_type.today()

        existing = db.query(Laufzettel).filter(
            Laufzettel.uid == uid,
            Laufzettel.date == entry_date,
        ).first()
        if existing:
            return JSONResponse(status_code=400, content={"detail": f"Laufzettel for {uid} on {entry_date} already exists"})

        # Try to fill owner info from registered tag if not provided
        known = db.query(RFIDTag).filter(RFIDTag.uid == uid, RFIDTag.active == 1).first()
        start_dt = None
        if data.start:
            try:
                start_dt = datetime.fromisoformat(data.start)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid start datetime format"})

        lz = Laufzettel(
            uid=uid,
            date=entry_date,
            start=start_dt,
            owner_name=data.owner_name or (known.owner_name if known else None),
            member_id=data.member_id or (known.member_id if known else None),
            nodes=json.dumps([]),
        )
        db.add(lz)
        db.commit()
        db.refresh(lz)
        d = lz.to_dict()
        d["material"] = []
        return d
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.get("/api/laufzettel")
async def get_laufzettel(uid: str = None, date: str = None):
    """List all Laufzettel entries, optionally filtered by uid or date"""
    db: Session = SessionLocal()
    try:
        query = db.query(Laufzettel)
        if uid:
            query = query.filter(Laufzettel.uid == uid.upper())
        if date:
            try:
                from datetime import date as dt_date
                parsed_date = dt_date.fromisoformat(date)
                query = query.filter(Laufzettel.date == parsed_date)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid date format, use YYYY-MM-DD"})
        entries = query.order_by(Laufzettel.date.desc(), Laufzettel.start.desc()).all()
        result = []
        for lz in entries:
            d = lz.to_dict()
            materials = db.query(LaufzettelMaterial).filter(
                LaufzettelMaterial.laufzettel_id == lz.id
            ).all()
            d["material"] = [m.to_dict() for m in materials]
            result.append(d)
        return result
    finally:
        db.close()


@app.get("/api/laufzettel/{laufzettel_id}")
async def get_laufzettel_detail(laufzettel_id: int):
    """Get a single Laufzettel with its material entries"""
    db: Session = SessionLocal()
    try:
        lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
        if not lz:
            return JSONResponse(status_code=404, content={"detail": "Laufzettel not found"})
        d = lz.to_dict()
        materials = db.query(LaufzettelMaterial).filter(
            LaufzettelMaterial.laufzettel_id == lz.id
        ).all()
        d["material"] = [m.to_dict() for m in materials]
        return d
    finally:
        db.close()


@app.get("/api/tags/{uid}/laufzettel")
async def get_laufzettel_for_tag(uid: str):
    """Get all Laufzettel entries for a specific tag"""
    db: Session = SessionLocal()
    try:
        entries = db.query(Laufzettel).filter(
            Laufzettel.uid == uid.upper()
        ).order_by(Laufzettel.date.desc()).all()
        result = []
        for lz in entries:
            d = lz.to_dict()
            materials = db.query(LaufzettelMaterial).filter(
                LaufzettelMaterial.laufzettel_id == lz.id
            ).all()
            d["material"] = [m.to_dict() for m in materials]
            result.append(d)
        return result
    finally:
        db.close()


@app.put("/api/laufzettel/{laufzettel_id}")
async def update_laufzettel(laufzettel_id: int, data: LaufzettelUpdate):
    """Update editable fields of a Laufzettel"""
    db: Session = SessionLocal()
    try:
        lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
        if not lz:
            return JSONResponse(status_code=404, content={"detail": "Laufzettel not found"})
        if data.owner_name is not None:
            lz.owner_name = data.owner_name
        if data.member_id is not None:
            lz.member_id = data.member_id
        if data.start is not None:
            try:
                lz.start = datetime.fromisoformat(data.start)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid start datetime format"})
        db.commit()
        db.refresh(lz)
        d = lz.to_dict()
        materials = db.query(LaufzettelMaterial).filter(
            LaufzettelMaterial.laufzettel_id == lz.id
        ).all()
        d["material"] = [m.to_dict() for m in materials]
        return d
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.post("/api/laufzettel/{laufzettel_id}/material")
async def add_material(laufzettel_id: int, mat: MaterialCreate):
    """Add a material entry to a Laufzettel"""
    db: Session = SessionLocal()
    try:
        lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
        if not lz:
            return JSONResponse(status_code=404, content={"detail": "Laufzettel not found"})
        new_mat = LaufzettelMaterial(
            laufzettel_id=laufzettel_id,
            name=mat.name,
            menge=mat.menge,
            variante_id=mat.variante_id,
            unit=mat.unit,
            laenge_cm=mat.laenge_cm,
            breite_cm=mat.breite_cm,
            hoehe_cm=mat.hoehe_cm,
            calculated_price=mat.calculated_price,
        )
        db.add(new_mat)
        db.commit()
        db.refresh(new_mat)
        return new_mat.to_dict()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.put("/api/laufzettel/{laufzettel_id}/material/{material_id}")
async def update_material(laufzettel_id: int, material_id: int, mat: MaterialUpdate):
    """Update a material entry"""
    db: Session = SessionLocal()
    try:
        existing = db.query(LaufzettelMaterial).filter(
            LaufzettelMaterial.id == material_id,
            LaufzettelMaterial.laufzettel_id == laufzettel_id,
        ).first()
        if not existing:
            return JSONResponse(status_code=404, content={"detail": "Material entry not found"})
        if mat.name is not None:
            existing.name = mat.name
        if mat.menge is not None:
            existing.menge = mat.menge
        if mat.variante_id is not None:
            existing.variante_id = mat.variante_id
        if mat.unit is not None:
            existing.unit = mat.unit
        if mat.laenge_cm is not None:
            existing.laenge_cm = mat.laenge_cm
        if mat.breite_cm is not None:
            existing.breite_cm = mat.breite_cm
        if mat.hoehe_cm is not None:
            existing.hoehe_cm = mat.hoehe_cm
        if mat.calculated_price is not None:
            existing.calculated_price = mat.calculated_price
        db.commit()
        db.refresh(existing)
        return existing.to_dict()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.delete("/api/laufzettel/{laufzettel_id}/material/{material_id}")
async def delete_material(laufzettel_id: int, material_id: int):
    """Delete a material entry from a Laufzettel"""
    db: Session = SessionLocal()
    try:
        existing = db.query(LaufzettelMaterial).filter(
            LaufzettelMaterial.id == material_id,
            LaufzettelMaterial.laufzettel_id == laufzettel_id,
        ).first()
        if not existing:
            return JSONResponse(status_code=404, content={"detail": "Material entry not found"})
        db.delete(existing)
        db.commit()
        return {"success": True, "message": f"Material entry {material_id} deleted"}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


# ── Katalog API ──────────────────────────────────────────────────────────────

@app.get("/api/katalog")
async def get_katalog():
    """Full catalog tree: locations → kategorien → varianten"""
    db: Session = SessionLocal()
    try:
        locations = db.query(Location).order_by(Location.name).all()
        result = []
        for loc in locations:
            kats = db.query(MaterialKategorie).filter(
                MaterialKategorie.location_id == loc.id
            ).order_by(MaterialKategorie.name).all()
            kat_list = []
            for kat in kats:
                variants = db.query(MaterialVariante).filter(
                    MaterialVariante.kategorie_id == kat.id
                ).order_by(MaterialVariante.name).all()
                k = kat.to_dict()
                k["varianten"] = [v.to_dict() for v in variants]
                kat_list.append(k)
            loc_data = loc.to_dict()
            loc_data["kategorien"] = kat_list
            result.append(loc_data)
        return result
    finally:
        db.close()


@app.get("/api/katalog/locations")
async def list_locations():
    db: Session = SessionLocal()
    try:
        return [loc.to_dict() for loc in db.query(Location).order_by(Location.name).all()]
    finally:
        db.close()


@app.post("/api/katalog/locations")
async def create_location(data: LocationCreate):
    db: Session = SessionLocal()
    try:
        loc = Location(name=data.name)
        db.add(loc)
        db.commit()
        db.refresh(loc)
        return loc.to_dict()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.put("/api/katalog/locations/{loc_id}")
async def update_location(loc_id: int, data: LocationUpdate):
    db: Session = SessionLocal()
    try:
        loc = db.query(Location).filter(Location.id == loc_id).first()
        if not loc:
            return JSONResponse(status_code=404, content={"detail": "Location not found"})
        if data.name is not None:
            loc.name = data.name
        db.commit()
        db.refresh(loc)
        return loc.to_dict()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.delete("/api/katalog/locations/{loc_id}")
async def delete_location(loc_id: int):
    db: Session = SessionLocal()
    try:
        loc = db.query(Location).filter(Location.id == loc_id).first()
        if not loc:
            return JSONResponse(status_code=404, content={"detail": "Location not found"})
        db.delete(loc)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.get("/api/katalog/kategorien")
async def list_kategorien(location_id: int = None):
    db: Session = SessionLocal()
    try:
        q = db.query(MaterialKategorie)
        if location_id:
            q = q.filter(MaterialKategorie.location_id == location_id)
        return [k.to_dict() for k in q.order_by(MaterialKategorie.name).all()]
    finally:
        db.close()


@app.post("/api/katalog/kategorien")
async def create_kategorie(data: KategorieCreate):
    db: Session = SessionLocal()
    try:
        kat = MaterialKategorie(
            location_id=data.location_id,
            name=data.name,
            pricing_model=data.pricing_model,
            unit=data.unit,
        )
        db.add(kat)
        db.commit()
        db.refresh(kat)
        return kat.to_dict()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.put("/api/katalog/kategorien/{kat_id}")
async def update_kategorie(kat_id: int, data: KategorieUpdate):
    db: Session = SessionLocal()
    try:
        kat = db.query(MaterialKategorie).filter(MaterialKategorie.id == kat_id).first()
        if not kat:
            return JSONResponse(status_code=404, content={"detail": "Kategorie not found"})
        if data.name is not None:
            kat.name = data.name
        if data.pricing_model is not None:
            kat.pricing_model = data.pricing_model
        if data.unit is not None:
            kat.unit = data.unit
        db.commit()
        db.refresh(kat)
        return kat.to_dict()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.delete("/api/katalog/kategorien/{kat_id}")
async def delete_kategorie(kat_id: int):
    db: Session = SessionLocal()
    try:
        kat = db.query(MaterialKategorie).filter(MaterialKategorie.id == kat_id).first()
        if not kat:
            return JSONResponse(status_code=404, content={"detail": "Kategorie not found"})
        db.delete(kat)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.get("/api/katalog/varianten")
async def list_varianten(kategorie_id: int = None):
    db: Session = SessionLocal()
    try:
        q = db.query(MaterialVariante)
        if kategorie_id:
            q = q.filter(MaterialVariante.kategorie_id == kategorie_id)
        return [v.to_dict() for v in q.order_by(MaterialVariante.name).all()]
    finally:
        db.close()


@app.post("/api/katalog/varianten")
async def create_variante(data: VarianteCreate):
    db: Session = SessionLocal()
    try:
        v = MaterialVariante(
            kategorie_id=data.kategorie_id,
            name=data.name,
            price=data.price,
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.to_dict()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.put("/api/katalog/varianten/{var_id}")
async def update_variante(var_id: int, data: VarianteUpdate):
    db: Session = SessionLocal()
    try:
        v = db.query(MaterialVariante).filter(MaterialVariante.id == var_id).first()
        if not v:
            return JSONResponse(status_code=404, content={"detail": "Variante not found"})
        if data.name is not None:
            v.name = data.name
        if data.price is not None:
            v.price = data.price
        db.commit()
        db.refresh(v)
        return v.to_dict()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.delete("/api/katalog/varianten/{var_id}")
async def delete_variante(var_id: int):
    db: Session = SessionLocal()
    try:
        v = db.query(MaterialVariante).filter(MaterialVariante.id == var_id).first()
        if not v:
            return JSONResponse(status_code=404, content={"detail": "Variante not found"})
        db.delete(v)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()


@app.get("/katalog", response_class=HTMLResponse)
async def katalog_page(request: Request):
    """Render Katalog management page"""
    return templates.TemplateResponse("katalog.html", {"request": request})


@app.get("/laufzettel", response_class=HTMLResponse)
async def laufzettel_page(request: Request):
    """Render Laufzettel list page"""
    return templates.TemplateResponse("laufzettel.html", {"request": request})


@app.get("/laufzettel/{laufzettel_id}", response_class=HTMLResponse)
async def laufzettel_detail_page(request: Request, laufzettel_id: int):
    """Render Laufzettel detail/edit page"""
    db: Session = SessionLocal()
    try:
        lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
        if not lz:
            raise HTTPException(status_code=404, detail="Laufzettel not found")
        return templates.TemplateResponse(
            "laufzettel-detail.html", {"request": request, "laufzettel_id": laufzettel_id}
        )
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
MakerPi GroundControl - Main FastAPI Application
MQTT Broker integration with SQLite database and Web UI
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
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


# Create tables
Base.metadata.create_all(bind=engine)

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

    def publish_command(self, device_id: str, command: str, payload: str = ""):
        """Publish a command to a device via MQTT"""
        topic = f"{device_id}/command"
        try:
            result = self.client.publish(topic, payload.encode("utf-8") if payload else b"", qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Command sent: {topic} -> {command}")
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
async def send_device_command(device_id: str, command: str):
    """Send a command to a device via MQTT"""
    if not mqtt_client:
        return JSONResponse(status_code=503, content={"success": False, "error": "MQTT not connected"})

    if not mqtt_client.connected:
        return JSONResponse(status_code=503, content={"success": False, "error": "MQTT not connected"})

    success = mqtt_client.publish_command(device_id, command)
    return {"success": success, "command": command, "device_id": device_id}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

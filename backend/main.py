"""
MakerPi GroundControl - Main FastAPI Application
MQTT Broker integration with SQLite database and Web UI
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
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


# Database Models
class MQTTMessage(Base):
    __tablename__ = "mqtt_messages"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    payload = Column(Text)
    qos = Column(Integer)
    retained = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "topic": self.topic,
            "payload": self.payload,
            "qos": self.qos,
            "retained": bool(self.retained),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True)
    name = Column(String)
    last_seen = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="unknown")

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "name": self.name,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "status": self.status,
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
                    device = db.query(Device).filter(Device.device_id == device_id).first()
                    if device:
                        device.last_seen = datetime.utcnow()
                        device.status = "online"
                    else:
                        # Create new device
                        device = Device(device_id=device_id, name=device_id, status="online")
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
        "timestamp": datetime.utcnow().isoformat(),
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

"""MQTT client for core module"""

import json
import logging
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

from backend.config import MQTT_BROKER, MQTT_PORT
from .db import SessionLocal
from .models import MQTTMessage, Device, TagScan

logger = logging.getLogger(__name__)
mqtt_client = None


def _utcnow():
    return datetime.now(timezone.utc)


def init_mqtt():
    """Initialize and connect MQTT client"""
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")


def shutdown_mqtt():
    """Disconnect MQTT client"""
    global mqtt_client
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        logger.info("Disconnected from MQTT broker")


def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        logger.info("Connected to MQTT broker, subscribing to #")
        client.subscribe("#")
    else:
        logger.error(f"MQTT connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Handle incoming MQTT message"""
    try:
        payload_str = msg.payload.decode("utf-8") if msg.payload else ""
    except UnicodeDecodeError:
        payload_str = str(msg.payload)
    
    # Store message
    db = SessionLocal()
    try:
        message = MQTTMessage(
            topic=msg.topic,
            payload=payload_str,
            qos=msg.qos,
            retained=1 if msg.retain else 0,
        )
        db.add(message)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to store MQTT message: {e}")
        db.rollback()
    finally:
        db.close()
    
    # Handle specific message types
    try:
        handle_device_message(msg.topic, payload_str)
    except Exception as e:
        logger.error(f"Error handling device message: {e}")


def handle_device_message(topic: str, payload: str):
    """Process device-related messages"""
    parts = topic.split("/")
    if len(parts) < 2:
        return
    
    device_id = parts[0]
    subtopic = parts[1] if len(parts) > 1 else ""
    
    db = SessionLocal()
    try:
        # Update device last_seen
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            device = Device(device_id=device_id, name=device_id)
            db.add(device)
        device.last_seen = _utcnow()
        
        # Handle status updates
        if subtopic == "status":
            try:
                data = json.loads(payload)
                device.status = data.get("status", "unknown")
            except json.JSONDecodeError:
                device.status = payload
        
        # Handle NFC scan
        if subtopic == "scan":
            try:
                data = json.loads(payload)
                uid = data.get("uid", "").upper()
                validated = 0
                owner_name = None
                
                # Check against members database
                from backend.members.db import SessionLocal as MembersSession
                members_db = MembersSession()
                try:
                    from backend.members.models import RFIDTag
                    tag = members_db.query(RFIDTag).filter(
                        RFIDTag.uid == uid, RFIDTag.active == 1
                    ).first()
                    if tag:
                        validated = 1
                        owner_name = tag.owner_name
                finally:
                    members_db.close()
                
                scan = TagScan(
                    uid=uid,
                    device_id=device_id,
                    validated=validated,
                    owner_name=owner_name,
                    tag_type=data.get("type"),
                    atqa=data.get("atqa"),
                    sak=data.get("sak"),
                )
                db.add(scan)
                
                # Auto-create Laufzettel for validated scans
                if validated:
                    from datetime import date as dt_date
                    from backend.laufzettel.db import SessionLocal as LaufzettelSession
                    from backend.laufzettel.models import Laufzettel
                    
                    lauf_db = LaufzettelSession()
                    try:
                        today = dt_date.today()
                        existing = lauf_db.query(Laufzettel).filter(
                            Laufzettel.uid == uid,
                            Laufzettel.date == today,
                        ).first()
                        if not existing:
                            new_lz = Laufzettel(
                                uid=uid,
                                date=today,
                                start=_utcnow(),
                                owner_name=owner_name,
                                nodes=json.dumps([device_id]),
                            )
                            lauf_db.add(new_lz)
                            lauf_db.commit()
                        else:
                            # Add device to nodes if not present
                            nodes = json.loads(existing.nodes or "[]")
                            if device_id not in nodes:
                                nodes.append(device_id)
                                existing.nodes = json.dumps(nodes)
                                lauf_db.commit()
                    finally:
                        lauf_db.close()
            except json.JSONDecodeError:
                pass
        
        db.commit()
    except Exception as e:
        logger.error(f"Error processing device message: {e}")
        db.rollback()
    finally:
        db.close()

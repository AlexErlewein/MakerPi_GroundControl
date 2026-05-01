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

# SSE subscribers for NFC scan events: list of (asyncio.Queue, asyncio.AbstractEventLoop)
scan_subscribers: list = []


def _utcnow():
    return datetime.now(timezone.utc)


def _notify_scan_subscribers(uid: str, device_id: str):
    """Push a scan event to all active SSE subscribers (thread-safe)."""
    event = {"uid": uid, "device_id": device_id}
    dead = []
    for queue, loop in scan_subscribers:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, event)
        except Exception:
            dead.append((queue, loop))
    for entry in dead:
        scan_subscribers.remove(entry)


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


def send_card_write_command(device_id: str, member_id: str, name: str, email: str, signature: str, request_id: str = "") -> bool:
    """Send a write command to a PicoW NFC Reader to write member data to a card.

    Args:
        device_id: The PicoW device ID (e.g., "picow_nfc_01")
        member_id: Member ID to write to card
        name: Member name to write to card
        email: Member email to write to card
        signature: HMAC signature for verification
        request_id: Optional request ID for tracking

    Returns:
        True if command was sent successfully
    """
    global mqtt_client
    if not mqtt_client:
        logger.error("MQTT client not initialized")
        return False

    topic = f"{device_id}/command"
    payload = json.dumps({
        "action": "write_card",
        "member_id": member_id,
        "name": name,
        "email": email,
        "signature": signature,
        "sector": 1,
        "request_id": request_id
    })

    try:
        result = mqtt_client.publish(topic, payload, qos=1)
        if result.rc == 0:
            logger.info(f"Sent write command to {device_id} for member {member_id}")
            return True
        else:
            logger.error(f"Failed to send write command to {device_id}: {result.rc}")
            return False
    except Exception as e:
        logger.error(f"Error sending write command: {e}")
        return False


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
        
        # Handle status updates (heartbeat or status subtopic)
        if subtopic in ("status", "heartbeat"):
            try:
                data = json.loads(payload)
                device.status = data.get("status", "online")
                nfc_ok = data.get("nfc_ok")
                if nfc_ok is not None:
                    device.nfc_ok = 1 if nfc_ok else 0
            except json.JSONDecodeError:
                device.status = payload
        
        # Handle NFC scan (subtopic 'scan' or 'tag')
        if subtopic in ("scan", "tag"):
            try:
                data = json.loads(payload)
                uid = data.get("uid", "").upper()
                validated = 0
                owner_name = None
                
                logger.info("[SCAN] Received uid=%r device_id=%r", uid, device_id)
                # Check against members database
                from backend.members.db import SessionLocal as MembersSession
                members_db = MembersSession()
                mitglied_db_id = None
                try:
                    from backend.members.models import RFIDTag, Mitglied
                    # Primary: check Mitglied.nfc_uid (the card enrolled via Mitglieder UI)
                    mitglied = members_db.query(Mitglied).filter(
                        Mitglied.nfc_uid == uid
                    ).first()
                    if mitglied:
                        validated = 1
                        owner_name = mitglied.name
                        mitglied_db_id = mitglied.id
                        logger.info("[SCAN] Matched Mitglied.nfc_uid: name=%r id=%s", owner_name, mitglied_db_id)
                    else:
                        logger.info("[SCAN] uid=%r not found in Mitglied.nfc_uid, checking RFIDTag", uid)
                        # Fallback: legacy RFIDTag table
                        tag = members_db.query(RFIDTag).filter(
                            RFIDTag.uid == uid, RFIDTag.active == 1
                        ).first()
                        if tag:
                            validated = 1
                            owner_name = tag.owner_name
                            logger.info("[SCAN] Matched RFIDTag: owner=%r member_id=%r", owner_name, tag.member_id)
                            # Try to resolve mitglied_id via member_id field
                            if tag.member_id:
                                m = members_db.query(Mitglied).filter(
                                    Mitglied.member_id == tag.member_id
                                ).first()
                                if m:
                                    mitglied_db_id = m.id
                        else:
                            logger.warning("[SCAN] uid=%r not found in Mitglied.nfc_uid or RFIDTag — unvalidated", uid)
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
                
                # Notify SSE subscribers about this scan
                logger.info("[SCAN] Notifying %d SSE subscriber(s) uid=%r device_id=%r", len(scan_subscribers), uid, device_id)
                _notify_scan_subscribers(uid, device_id)

                # Publish scan result to LilyGo display (and other displays)
                global mqtt_client
                if mqtt_client:
                    try:
                        response_payload = json.dumps({
                            "uid": uid,
                            "owner_name": owner_name,
                            "member_id": str(mitglied_db_id) if mitglied_db_id else None,
                            "validated": bool(validated),
                            "source": "REMOTE"
                        })
                        mqtt_client.publish("lilygo/user_info", response_payload)
                        logger.info("[SCAN] Published to lilygo/user_info: uid=%r validated=%s", uid, validated)
                    except Exception as e:
                        logger.error(f"[SCAN] Failed to publish to lilygo/user_info: {e}")

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
                                mitglied_id=mitglied_db_id,
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
                            # Update mitglied_id if not yet set
                            if not existing.mitglied_id and mitglied_db_id:
                                existing.mitglied_id = mitglied_db_id
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

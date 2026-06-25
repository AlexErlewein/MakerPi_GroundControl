"""MQTT client for core module"""

import hashlib
import json
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from backend.config import MQTT_BROKER, MQTT_PORT

from .db import SessionLocal
from .models import Device, MQTTMessage, TagScan

# Push notification support (import at module level, calls wrapped in try/except)
try:
    from backend.push.routes import send_push_notification
except Exception:
    send_push_notification = None  # Optional module
    pass

logger = logging.getLogger(__name__)
mqtt_client = None

# SSE subscribers for NFC scan events: list of (asyncio.Queue, asyncio.AbstractEventLoop)
scan_subscribers: list = []

# Kaffeemaschine debounce: last scan timestamp per UID (to prevent accidental double-counting)
# Format: {uid: datetime}
_kaffeemaschine_last_scan: dict = {}
KAFFEEMASCHINE_DEBOUNCE_S = 15  # seconds between Kaffee increments for same card

# Kuehlschrank debounce: last scan timestamp per UID (to prevent accidental double-counting)
# Format: {uid: datetime}
_kuehlschrank_last_scan: dict = {}
KUEHLSCHRANK_DEBOUNCE_S = 15  # seconds between Limo increments for same card

# Scan deduplication: drop duplicate on_message calls for the same uid+device within 2s.
# The paho-mqtt client can deliver messages twice when the connection is unstable.
_scan_dedup: dict = {}  # {(device_id, uid): datetime}
SCAN_DEDUP_S = 2

# Payload-level dedup: prevents storing identical messages that arrive within 1s.
# Some devices (e.g. PicoW NFC readers) publish the same payload twice in rapid succession.
_payload_dedup: dict = {}  # {(topic, payload_hash): datetime}
PAYLOAD_DEDUP_S = 1


def _utcnow():
    return datetime.now(timezone.utc)


def should_store_message(topic: str) -> bool:
    """Return False for heartbeat/availability/status noise, True for meaningful messages."""
    if topic.startswith("zigbee2mqtt"):
        return False
    if "/heartbeat" in topic or "/availability" in topic:
        return False
    if "/status" in topic:
        return False
    if topic.endswith("/online") or topic.endswith("/offline"):
        return False
    # Don't store our own user_info publishes — we publish to lilygo/user_info
    # and {device}/user_info but subscribe to #, so they echo back to us
    if topic.endswith("/user_info"):
        return False
    return True


def _notify_scan_subscribers(uid: str, device_id: str):
    """Push a scan event to all active SSE subscribers (thread-safe).

    Subscribers are now stored as (queue, loop, allowed_device) tuples.
    If allowed_device is set, only events from that device are sent.
    """
    event = {"uid": uid, "device_id": device_id}
    dead = []
    for entry in scan_subscribers:
        # Handle both old (queue, loop) and new (queue, loop, allowed_device) formats
        if len(entry) == 2:
            queue, loop = entry
            allowed_device = None
        else:
            queue, loop, allowed_device = entry

        # Skip if this subscriber is paired to a different device
        if allowed_device and allowed_device != device_id:
            continue

        try:
            loop.call_soon_threadsafe(queue.put_nowait, event)
        except Exception:
            dead.append(entry)
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


def send_card_write_command(
    device_id: str,
    member_id: str,
    name: str,
    email: str,
    signature: str,
    sector_key: str = "",
    request_id: str = "",
) -> bool:
    """Send a write command to a PicoW NFC Reader to write member data to a card.

    Args:
        device_id: The PicoW device ID (e.g., "picow_nfc_01")
        member_id: Member ID to write to card
        name: Member name to write to card
        email: Member email to write to card
        signature: HMAC signature for verification
        sector_key: 12-char hex Mifare sector key for sector 1 authentication
        request_id: Optional request ID for tracking

    Returns:
        True if command was sent successfully
    """
    global mqtt_client
    if not mqtt_client:
        logger.error("MQTT client not initialized")
        return False

    topic = f"{device_id}/command"
    payload = json.dumps(
        {
            "action": "write_card",
            "member_id": member_id,
            "name": name,
            "email": email,
            "signature": signature,
            "sector_key": sector_key,
            "sector": 1,
            "request_id": request_id,
        }
    )

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


def send_device_activation_command(
    device_id: str, member_id: int, member_name: str, allowed: bool
) -> bool:
    """Send an activation command to a device indicating whether a member is allowed.

    Args:
        device_id: The device ID (e.g., "picow_nfc_01")
        member_id: The member's database ID
        member_name: The member's name
        allowed: Whether the member has permission to use this device

    Returns:
        True if command was sent successfully
    """
    global mqtt_client
    if not mqtt_client:
        logger.error("MQTT client not initialized")
        return False

    topic = f"{device_id}/command"
    payload = json.dumps(
        {
            "action": "activate",
            "member_id": member_id,
            "member_name": member_name,
            "allowed": allowed,
        }
    )

    try:
        result = mqtt_client.publish(topic, payload, qos=1)
        if result.rc == 0:
            logger.info(
                f"Sent activation command to {device_id}: member={member_id} allowed={allowed}"
            )
            return True
        else:
            logger.error(
                f"Failed to send activation command to {device_id}: {result.rc}"
            )
            return False
    except Exception as e:
        logger.error(f"Error sending activation command: {e}")
        return False


def _publish_nfc_config() -> None:
    """Broadcast sector key to all PicoW devices as a retained MQTT message.

    PicoW devices subscribe to groundcontrol/nfc/config at startup and use the
    sector_key to authenticate to Mifare Classic sector 1 during reads and writes.
    The retained flag ensures late-connecting devices receive it immediately.
    """
    global mqtt_client
    if not mqtt_client:
        return
    try:
        from backend.members.signature import get_mifare_sector_key

        payload = json.dumps(
            {"sector_key": get_mifare_sector_key(), "sector": 1, "version": 1}
        )
        mqtt_client.publish("groundcontrol/nfc/config", payload, qos=1, retain=True)
        logger.info("Published NFC sector key config to groundcontrol/nfc/config")
    except Exception as e:
        logger.error(f"Failed to publish NFC config: {e}")


def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        logger.info("Connected to MQTT broker, subscribing to #")
        client.subscribe("#")
        _publish_nfc_config()
    else:
        logger.error(f"MQTT connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Handle incoming MQTT message"""
    try:
        payload_str = msg.payload.decode("utf-8") if msg.payload else ""
    except UnicodeDecodeError:
        payload_str = str(msg.payload)

    # Payload-level dedup: skip storing + processing if identical message was
    # seen on this topic within the dedup window (catches device-side doubles)
    if payload_str:
        pd_key = (msg.topic, hashlib.sha256(payload_str.encode()).digest()[:8])
        pd_last = _payload_dedup.get(pd_key)
        pd_now = _utcnow()
        if pd_last and (pd_now - pd_last).total_seconds() < PAYLOAD_DEDUP_S:
            logger.debug("[DEDUP] Payload duplicate dropped: topic=%r", msg.topic)
            return
        _payload_dedup[pd_key] = pd_now

    # Store message (only if meaningful)
    if should_store_message(msg.topic):
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
        handle_device_message(msg.topic, payload_str, retained=bool(msg.retain))
    except Exception as e:
        logger.error(f"Error handling device message: {e}")


def handle_device_message(topic: str, payload: str, retained: bool = False):
    """Process device-related messages"""
    if topic.startswith("zigbee2mqtt"):
        return

    parts = topic.split("/")
    if len(parts) < 2:
        return

    device_id = parts[0]
    subtopic = parts[1] if len(parts) > 1 else ""

    # Skip our own outgoing publishes that echo back via the # subscription
    if subtopic == "user_info":
        return

    db = SessionLocal()
    try:
        # Update device last_seen - but skip auto-creation for retained messages.
        # Mosquitto replays retained messages at startup for devices that may no
        # longer exist; we only want devices to appear when they're actively live.
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            if not retained:
                device = Device(device_id=device_id, name=device_id)
                db.add(device)

        if device:
            device.last_seen = _utcnow()

        # Handle status updates (heartbeat or status subtopic)
        if subtopic in ("status", "heartbeat"):
            try:
                data = json.loads(payload)
                device.status = data.get("status", "online")
                nfc_ok = data.get("nfc_ok")
                if nfc_ok is not None:
                    device.nfc_ok = 1 if nfc_ok else 0
                # Update requires_permission from heartbeat if provided
                requires_permission = data.get("requires_permission")
                if requires_permission is not None:
                    device.requires_permission = 1 if requires_permission else 0
            except json.JSONDecodeError:
                device.status = payload

        # Handle NFC scan (subtopic 'scan' or 'tag')
        if subtopic in ("scan", "tag"):
            try:
                data = json.loads(payload)
                uid = data.get("uid", "").upper()

                # Dedup: paho-mqtt can deliver the same message twice on reconnect
                dedup_key = (device_id, uid)
                now_dt = _utcnow()
                last_seen = _scan_dedup.get(dedup_key)
                if last_seen and (now_dt - last_seen).total_seconds() < SCAN_DEDUP_S:
                    logger.debug(
                        "[SCAN] Duplicate dropped uid=%r device_id=%r", uid, device_id
                    )
                    return
                _scan_dedup[dedup_key] = now_dt

                validated = 0
                owner_name = None

                # Extract card-side data (written during enrollment)
                card_member_id = data.get("member_id")
                card_name = data.get("name")
                card_email = data.get("email")
                card_signature = data.get("signature")
                card_verified = None  # 3VL: None=legacy, 1=verified, 0=rejected

                logger.info("[SCAN] Received uid=%r device_id=%r", uid, device_id)
                # Check against members database
                from backend.members.db import SessionLocal as MembersSession

                members_db = MembersSession()
                mitglied_db_id = None
                member_id_str = None
                mitglied = None
                try:
                    from backend.members.models import Mitglied, RFIDTag

                    # Primary: check Mitglied.nfc_uid (the card enrolled via Mitglieder UI)
                    mitglied = (
                        members_db.query(Mitglied)
                        .filter(Mitglied.nfc_uid == uid)
                        .first()
                    )
                    if mitglied:
                        validated = 1
                        owner_name = mitglied.name
                        mitglied_db_id = mitglied.id
                        member_id_str = mitglied.member_id
                        logger.info(
                            "[SCAN] Matched Mitglied.nfc_uid: name=%r id=%s member_id=%r",
                            owner_name,
                            mitglied_db_id,
                            member_id_str,
                        )
                    else:
                        logger.info(
                            "[SCAN] uid=%r not found in Mitglied.nfc_uid, checking RFIDTag",
                            uid,
                        )
                        # Fallback: legacy RFIDTag table
                        tag = (
                            members_db.query(RFIDTag)
                            .filter(RFIDTag.uid == uid, RFIDTag.active == 1)
                            .first()
                        )
                        if tag:
                            validated = 1
                            owner_name = tag.owner_name
                            logger.info(
                                "[SCAN] Matched RFIDTag: owner=%r member_id=%r",
                                owner_name,
                                tag.member_id,
                            )
                            # Try to resolve mitglied_id via member_id field
                            if tag.member_id:
                                m = (
                                    members_db.query(Mitglied)
                                    .filter(Mitglied.member_id == tag.member_id)
                                    .first()
                                )
                                if m:
                                    mitglied_db_id = m.id
                                    member_id_str = m.member_id
                                    mitglied = m
                        else:
                            logger.warning(
                                "[SCAN] uid=%r not found in Mitglied.nfc_uid or RFIDTag — unvalidated",
                                uid,
                            )
                finally:
                    members_db.close()

                # Device permission check: member must have permission for this device
                # Skip check if device.requires_permission == False (e.g., Kaffeemaschine)
                # We separate member validation (known member) from device permission (access to specific device)
                device_validated = (
                    validated  # Whether member has permission for this specific device
                )
                if validated and mitglied_db_id:
                    # Check if device requires permission
                    device_requires_permission = True  # default for safety
                    if device and device.requires_permission is not None:
                        device_requires_permission = bool(device.requires_permission)

                    if device_requires_permission:
                        from backend.members.db import SessionLocal as MembersSession
                        from backend.members.models import DevicePermission

                        perm_db = MembersSession()
                        try:
                            # Check for specific device permission or wildcard ("*")
                            has_permission = (
                                perm_db.query(DevicePermission)
                                .filter(
                                    DevicePermission.member_id == mitglied_db_id,
                                    DevicePermission.device_id.in_([device_id, "*"]),
                                )
                                .first()
                            )

                            if not has_permission:
                                device_validated = (
                                    0  # Only device access denied, member still known
                                )
                                logger.warning(
                                    "[SCAN] uid=%r denied: member %s has no permission for device %s",
                                    uid,
                                    mitglied_db_id,
                                    device_id,
                                )
                        finally:
                            perm_db.close()
                    else:
                        logger.info(
                            "[SCAN] uid=%r allowed: device %s does not require permission",
                            uid,
                            device_id,
                        )

                # 3VL signature verification (runs after DB lookup so mitglied.name
                # is available as fallback when firmware omits name from payload)
                #   None = legacy card (no signature data present)
                #   1    = HMAC signature verified — card was issued by this server
                #   0    = HMAC signature present but invalid — possible clone attempt
                if card_signature and card_member_id:
                    from backend.members.signature import verify_card_signature

                    # Prefer DB values over card-provided data for signature verification.
                    # The HMAC was generated with DB data at enrollment, but cards may
                    # store truncated names (MIFARE block size limits) or a member_id
                    # that has since changed via easyVerein sync — using card-side data
                    # would produce a different hash and reject valid cards.
                    verify_name = (mitglied.name if mitglied else None) or card_name
                    verify_member_id = member_id_str or card_member_id
                    if verify_name:
                        if verify_card_signature(
                            verify_member_id, uid, verify_name, card_signature
                        ):
                            card_verified = 1
                            logger.info(
                                "[SCAN] Signature VERIFIED uid=%r member_id=%r (card=%r)",
                                uid,
                                verify_member_id,
                                card_member_id,
                            )
                        else:
                            card_verified = 0
                            logger.warning(
                                "[SCAN] Signature REJECTED uid=%r member_id=%r (card=%r) — possible clone attempt",
                                uid,
                                verify_member_id,
                                card_member_id,
                            )
                    else:
                        card_verified = 0
                        logger.warning(
                            "[SCAN] Signature unverifiable uid=%r member_id=%r — member not found in DB",
                            uid,
                            card_member_id,
                        )

                # Apply NFC_SIGNATURE_MODE rules
                from backend.config import NFC_SIGNATURE_MODE

                if card_verified == 0:
                    # Invalid signature always rejects regardless of mode
                    validated = 0
                elif NFC_SIGNATURE_MODE == "strict" and card_verified is None:
                    # Strict mode: cards without a signature are not accepted
                    validated = 0
                    logger.warning(
                        "[SCAN] uid=%r denied: no card signature in strict mode", uid
                    )

                scan = TagScan(
                    uid=uid,
                    device_id=device_id,
                    validated=validated,
                    owner_name=owner_name,
                    tag_type=data.get("tag_type"),
                    atqa=data.get("atqa"),
                    sak=data.get("sak"),
                    card_member_id=card_member_id,
                    card_name=card_name,
                    card_email=card_email,
                    card_signature=card_signature,
                    card_verified=card_verified,
                )
                db.add(scan)

                # Notify SSE subscribers about this scan
                logger.info(
                    "[SCAN] Notifying %d SSE subscriber(s) uid=%r device_id=%r",
                    len(scan_subscribers),
                    uid,
                    device_id,
                )
                _notify_scan_subscribers(uid, device_id)

                # Publish scan result to all displays
                global mqtt_client
                if mqtt_client:
                    try:
                        response_payload = json.dumps(
                            {
                                "uid": uid,
                                "owner_name": owner_name,
                                "member_id": str(mitglied_db_id)
                                if mitglied_db_id
                                else None,
                                "validated": bool(
                                    device_validated
                                ),  # Use device_validated for access control
                                "source": "REMOTE",
                            }
                        )
                        # Publish to legacy LilyGo channel (backward compat)
                        mqtt_client.publish("lilygo/user_info", response_payload)
                        # Publish to device-specific channel so each scanner sees its own result
                        mqtt_client.publish(f"{device_id}/user_info", response_payload)
                        logger.info(
                            "[SCAN] Published user_info to lilygo/user_info and %s/user_info: uid=%r validated=%s",
                            device_id,
                            uid,
                            device_validated,
                        )
                    except Exception as e:
                        logger.error(f"[SCAN] Failed to publish user_info: {e}")

                # Auto-create Laufzettel for known members (independent of device permission)
                # Create Laufzettel if we identified the member, even if device permission was denied
                # Device permission only controls whether the device is added to nodes, not Laufzettel creation
                if mitglied_db_id or member_id_str:
                    from datetime import (
                        date as dt_date,
                    )
                    from datetime import (
                        datetime as dt_datetime,
                    )
                    from datetime import (
                        timedelta,
                    )
                    from datetime import (
                        timezone as dt_timezone,
                    )

                    from backend.laufzettel.db import SessionLocal as LaufzettelSession
                    from backend.laufzettel.models import Laufzettel, LaufzettelMaterial

                    lauf_db = LaufzettelSession()
                    try:
                        today = dt_date.today()

                        # Handle stale open laufzettel from previous days before
                        # deciding whether to create a new one for today.
                        # Empty stale ones are deleted; non-empty ones are
                        # carried over into a today-dated laufzettel.
                        if mitglied_db_id:
                            try:
                                from backend.laufzettel.utils import (
                                    handle_stale_laufzettel,
                                )

                                handle_stale_laufzettel(mitglied_db_id, lauf_db, today)
                            except Exception:
                                logger.exception(
                                    "[SCAN] handle_stale_laufzettel failed for mitglied_id=%s",
                                    mitglied_db_id,
                                )

                        today_lz = (
                            lauf_db.query(Laufzettel)
                            .filter(
                                Laufzettel.uid == uid,
                                Laufzettel.date == today,
                            )
                            .all()
                        )
                        # Find the first open (unpaid) Laufzettel for today
                        open_lz = next(
                            (
                                lz
                                for lz in today_lz
                                if not lz.payment_method and not lz.deleted_at
                            ),
                            None,
                        )
                        # Dedup guard: skip if any laufzettel was created for this UID in last 5s
                        now_utc = dt_datetime.now(dt_timezone.utc).replace(tzinfo=None)
                        recently_created = any(
                            lz.created_at
                            and (now_utc - lz.created_at) < timedelta(seconds=5)
                            for lz in today_lz
                        )

                        # Check if this is the Kaffeemaschine device
                        is_kaffeemaschine = (
                            device.name and device.name.lower() == "kaffeemaschine"
                        )

                        # Check if this is the Kuehlschrank device
                        is_kuehlschrank = (
                            device.name and device.name.lower() == "kuehlschrank"
                        )

                        # Use locking to prevent race conditions when creating Laufzettel

                        # Lock any existing open Laufzettel for this UID today to prevent concurrent creation
                        locked_lz = (
                            lauf_db.query(Laufzettel)
                            .filter(
                                Laufzettel.uid == uid,
                                Laufzettel.date == today,
                                Laufzettel.payment_method.is_(None),
                            )
                            .with_for_update()
                            .first()
                        )

                        # Re-check after acquiring lock - another thread may have created one
                        if locked_lz:
                            open_lz = locked_lz

                        if is_kaffeemaschine and open_lz:
                            # Kaffeemaschine flow: add/increment Kaffee entry
                            # Debounce: check if enough time passed since last scan
                            global _kaffeemaschine_last_scan
                            last_scan = _kaffeemaschine_last_scan.get(uid)
                            now_dt = _utcnow()
                            if (
                                last_scan
                                and (now_dt - last_scan).total_seconds()
                                < KAFFEEMASCHINE_DEBOUNCE_S
                            ):
                                logger.info(
                                    "[KAFFEEMASCHINE] Debounced scan for uid=%s (%.1fs < %ds)",
                                    uid,
                                    (now_dt - last_scan).total_seconds(),
                                    KAFFEEMASCHINE_DEBOUNCE_S,
                                )
                                # Still update nodes but skip Kaffee increment
                                nodes = json.loads(open_lz.nodes or "[]")
                                if device_id not in nodes:
                                    nodes.append(device_id)
                                    open_lz.nodes = json.dumps(nodes)
                                    lauf_db.commit()
                            else:
                                # Update last scan timestamp and process Kaffee
                                _kaffeemaschine_last_scan[uid] = now_dt
                                existing_kaffee = (
                                    lauf_db.query(LaufzettelMaterial)
                                    .filter(
                                        LaufzettelMaterial.laufzettel_id == open_lz.id,
                                        LaufzettelMaterial.name == "Kaffee",
                                    )
                                    .first()
                                )
                                if existing_kaffee:
                                    # Increment amount by 1
                                    existing_kaffee.menge = (
                                        existing_kaffee.menge or 0
                                    ) + 1
                                    logger.info(
                                        "[KAFFEEMASCHINE] Incremented Kaffee count for laufzettel %s: now %s",
                                        open_lz.id,
                                        existing_kaffee.menge,
                                    )
                                else:
                                    # Create new Kaffee entry under Spenden (tax_rate=0, price=0)
                                    new_kaffee = LaufzettelMaterial(
                                        laufzettel_id=open_lz.id,
                                        name="Kaffee",
                                        menge=1,
                                        calculated_price=0.0,
                                        tax_rate=0.0,
                                    )
                                    lauf_db.add(new_kaffee)
                                    logger.info(
                                        "[KAFFEEMASCHINE] Added Kaffee entry to laufzettel %s",
                                        open_lz.id,
                                    )
                                # Also update nodes to include kaffeemaschine
                                nodes = json.loads(open_lz.nodes or "[]")
                                if device_id not in nodes:
                                    nodes.append(device_id)
                                    open_lz.nodes = json.dumps(nodes)
                                # Single commit for all Kaffeemaschine changes
                                lauf_db.commit()
                        elif is_kuehlschrank and open_lz:
                            # Kuehlschrank flow: add/increment Limo entry
                            # Debounce: check if enough time passed since last scan
                            global _kuehlschrank_last_scan
                            last_scan = _kuehlschrank_last_scan.get(uid)
                            now_dt = _utcnow()
                            if (
                                last_scan
                                and (now_dt - last_scan).total_seconds()
                                < KUEHLSCHRANK_DEBOUNCE_S
                            ):
                                logger.info(
                                    "[KUEHLSCHRANK] Debounced scan for uid=%s (%.1fs < %ds)",
                                    uid,
                                    (now_dt - last_scan).total_seconds(),
                                    KUEHLSCHRANK_DEBOUNCE_S,
                                )
                                # Still update nodes but skip Limo increment
                                nodes = json.loads(open_lz.nodes or "[]")
                                if device_id not in nodes:
                                    nodes.append(device_id)
                                    open_lz.nodes = json.dumps(nodes)
                                    lauf_db.commit()
                            else:
                                # Update last scan timestamp and process Limo
                                _kuehlschrank_last_scan[uid] = now_dt
                                existing_limo = (
                                    lauf_db.query(LaufzettelMaterial)
                                    .filter(
                                        LaufzettelMaterial.laufzettel_id == open_lz.id,
                                        LaufzettelMaterial.name == "Limo",
                                    )
                                    .first()
                                )
                                if existing_limo:
                                    # Increment amount by 1
                                    existing_limo.menge = (existing_limo.menge or 0) + 1
                                    logger.info(
                                        "[KUEHLSCHRANK] Incremented Limo count for laufzettel %s: now %s",
                                        open_lz.id,
                                        existing_limo.menge,
                                    )
                                else:
                                    # Create new Limo entry under Spenden (tax_rate=0, price=0)
                                    new_limo = LaufzettelMaterial(
                                        laufzettel_id=open_lz.id,
                                        name="Limo",
                                        menge=1,
                                        calculated_price=0.0,
                                        tax_rate=0.0,
                                    )
                                    lauf_db.add(new_limo)
                                    logger.info(
                                        "[KUEHLSCHRANK] Added Limo entry to laufzettel %s",
                                        open_lz.id,
                                    )
                                # Also update nodes to include kuehlschrank
                                nodes = json.loads(open_lz.nodes or "[]")
                                if device_id not in nodes:
                                    nodes.append(device_id)
                                    open_lz.nodes = json.dumps(nodes)
                                # Single commit for all Kuehlschrank changes
                                lauf_db.commit()
                        elif open_lz is None and not recently_created:
                            # No open Laufzettel – create a new one
                            # (covers first scan of day AND re-scan after all are paid)
                            # Only add device to nodes if member has permission for this device
                            nodes_list = [device_id] if device_validated else []
                            new_lz = Laufzettel(
                                uid=uid,
                                date=today,
                                start=_utcnow(),
                                owner_name=owner_name,
                                member_id=member_id_str,
                                mitglied_id=mitglied_db_id,
                                nodes=json.dumps(nodes_list),
                            )
                            lauf_db.add(new_lz)
                            lauf_db.commit()
                            lauf_db.refresh(new_lz)
                            # Push notification (non-critical)
                            try:
                                if send_push_notification:
                                    send_push_notification(
                                        title="Neuer Laufzettel erstellt",
                                        body=f"Laufzettel #{new_lz.id} — {owner_name or uid}",
                                        tag=f"laufzettel-{new_lz.id}",
                                        url=f"/laufzettel/{new_lz.id}",
                                    )
                            except Exception:
                                pass

                            # If this is the Kaffeemaschine, also add the first Kaffee entry
                            if is_kaffeemaschine:
                                new_kaffee = LaufzettelMaterial(
                                    laufzettel_id=new_lz.id,
                                    name="Kaffee",
                                    menge=1,
                                    calculated_price=0.0,
                                    tax_rate=0.0,
                                )
                                lauf_db.add(new_kaffee)
                                lauf_db.commit()
                                logger.info(
                                    "[KAFFEEMASCHINE] Added first Kaffee entry to new laufzettel %s",
                                    new_lz.id,
                                )

                            # If this is the Kuehlschrank, also add the first Limo entry
                            if is_kuehlschrank:
                                new_limo = LaufzettelMaterial(
                                    laufzettel_id=new_lz.id,
                                    name="Limo",
                                    menge=1,
                                    calculated_price=0.0,
                                    tax_rate=0.0,
                                )
                                lauf_db.add(new_limo)
                                lauf_db.commit()
                                logger.info(
                                    "[KUEHLSCHRANK] Added first Limo entry to new laufzettel %s",
                                    new_lz.id,
                                )
                        elif open_lz is not None:
                            # Update existing open Laufzettel (regular scanner, not Kaffeemaschine)
                            # Only add device to nodes if member has permission for this device
                            if device_validated:
                                nodes = json.loads(open_lz.nodes or "[]")
                                if device_id not in nodes:
                                    nodes.append(device_id)
                                open_lz.nodes = json.dumps(nodes)
                            if not open_lz.mitglied_id and mitglied_db_id:
                                open_lz.mitglied_id = mitglied_db_id
                            if not open_lz.member_id and member_id_str:
                                open_lz.member_id = member_id_str
                            lauf_db.commit()
                        # If recently_created is True, do nothing (dedup guard)
                    finally:
                        lauf_db.close()

                # Guest NFC Card Handling
                # If no member was found, check if this is a guest NFC tag.
                # Isolated in its own try/except so a failure here can never roll
                # back the TagScan insert in the main transaction.
                if not mitglied_db_id and not member_id_str and validated == 0:
                    try:
                        from backend.laufzettel.db import (
                            SessionLocal as LaufzettelSession,
                        )
                        from backend.laufzettel.models import Laufzettel

                        lauf_db = LaufzettelSession()
                        try:
                            from datetime import date as dt_date

                            # Look for active guest Laufzettel with this NFC tag
                            today = dt_date.today()
                            guest_lz = (
                                lauf_db.query(Laufzettel)
                                .filter(
                                    Laufzettel.guest_nfc_uid == uid,
                                    Laufzettel.date == today,
                                    Laufzettel.payment_method.is_(None),
                                    Laufzettel.deleted_at.is_(None),
                                )
                                .order_by(Laufzettel.created_at.desc())
                                .first()
                            )

                            if guest_lz:
                                logger.info(
                                    "[GUEST_SCAN] Found guest Laufzettel %s for NFC tag %s",
                                    guest_lz.id,
                                    uid,
                                )

                                # Update existing guest Laufzettel
                                nodes = json.loads(guest_lz.nodes or "[]")
                                if device_id not in nodes:
                                    nodes.append(device_id)
                                    guest_lz.nodes = json.dumps(nodes)

                                # Update timestamp if not set
                                if not guest_lz.start:
                                    guest_lz.start = _utcnow()

                                lauf_db.commit()

                                # Update scan record to show guest info
                                scan.owner_name = guest_lz.owner_name or "Guest"
                                scan.validated = 1  # Mark as validated for guest access

                                # Publish guest scan result
                                if mqtt_client:
                                    try:
                                        response_payload = json.dumps(
                                            {
                                                "uid": uid,
                                                "owner_name": guest_lz.owner_name
                                                or "Guest",
                                                "guest_id": guest_lz.guest_id,
                                                "laufzettel_id": guest_lz.id,
                                                "validated": True,
                                                "source": "GUEST",
                                            }
                                        )
                                        mqtt_client.publish(
                                            "lilygo/user_info", response_payload
                                        )
                                        mqtt_client.publish(
                                            f"{device_id}/user_info", response_payload
                                        )
                                        logger.info(
                                            "[GUEST_SCAN] Published guest user_info: uid=%r laufzettel_id=%s",
                                            uid,
                                            guest_lz.id,
                                        )
                                    except Exception as e:
                                        logger.error(
                                            f"[GUEST_SCAN] Failed to publish user_info: {e}"
                                        )
                            else:
                                logger.info(
                                    "[GUEST_SCAN] NFC tag %s not linked to any active guest session",
                                    uid,
                                )
                        finally:
                            lauf_db.close()
                    except Exception as e:
                        logger.error("[GUEST_SCAN] Guest NFC handling failed: %s", e)
            except json.JSONDecodeError:
                pass

        db.commit()
    except Exception as e:
        logger.error(f"Error processing device message: {e}")
        db.rollback()
    finally:
        db.close()

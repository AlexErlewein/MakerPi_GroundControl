"""Core routes - devices, messages, status, dashboard"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .models import MQTTMessage, Device, TagScan, ZigbeeDevice
from .mqtt import init_mqtt, shutdown_mqtt, scan_subscribers
import backend.config as _app_config

router = APIRouter()


# ── System Status Check Functions ────────────────────────────────────────────


async def check_docs_status() -> dict:
    """Check if docs server on port 8001 is responding."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://localhost:8001")
            if response.status_code < 500:
                return {"status": "ok", "message": "Online"}
    except Exception:
        pass
    return {"status": "error", "message": "Offline"}


def check_zigbee_status() -> dict:
    """Check if zigbee2mqtt frontend (port 8090) and USB device are accessible."""
    import socket

    status_parts = []
    errors = []

    # Check port 8090 accessibility
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 8090))
        sock.close()
        if result == 0:
            status_parts.append("Web UI accessible")
        else:
            errors.append("Web UI offline")
    except Exception:
        errors.append("Web UI check failed")

    # Check USB device
    try:
        usb_path = Path("/dev/ttyUSB0")
        if usb_path.exists():
            status_parts.append("USB connected")
        else:
            # Try alternative path
            usb_path_alt = Path("/dev/ttyACM0")
            if usb_path_alt.exists():
                status_parts.append("USB connected (ACM0)")
            else:
                errors.append("USB not found")
    except Exception:
        errors.append("USB check failed")

    if errors and not status_parts:
        return {"status": "error", "message": ", ".join(errors)}
    elif status_parts and not errors:
        return {"status": "ok", "message": ", ".join(status_parts)}
    else:
        return {
            "status": "warning",
            "message": f"{', '.join(status_parts)}; {', '.join(errors)}",
        }


def check_database_status() -> dict:
    """Check if Litestream is running and B2 connection is working."""
    status_parts = []
    errors = []

    # Check if Litestream process is running
    try:
        result = subprocess.run(
            ["pgrep", "-f", "litestream"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            status_parts.append("Litestream running")
        else:
            errors.append("Litestream not running")
    except Exception:
        errors.append("Litestream check failed")

    # Check B2 connection via litestream config
    if _app_config.LITESTREAM_ENABLED:
        try:
            cfg_path = Path("config/litestream.yml")
            if cfg_path.exists():
                status_parts.append("Config present")
            else:
                errors.append("Config missing")
        except Exception:
            errors.append("Config check failed")
    else:
        status_parts.append("Litestream disabled")

    if errors and not status_parts:
        return {"status": "error", "message": ", ".join(errors)}
    elif status_parts and not errors:
        return {"status": "ok", "message": ", ".join(status_parts)}
    else:
        return {
            "status": "warning",
            "message": f"{', '.join(status_parts)}; {', '.join(errors)}",
        }


def check_gdrive_status() -> dict:
    """Check if Google Drive authentication is working."""
    try:
        from backend.gdrive import get_drive_service

        service = get_drive_service()
        if service:
            return {"status": "ok", "message": "Connected"}
        else:
            return {"status": "error", "message": "Not configured"}
    except Exception as e:
        return {"status": "error", "message": f"Connection failed: {str(e)}"}


# ── Routes ───────────────────────────────────────────────────────────────────


@router.on_event("startup")
async def startup():
    init_db()
    init_mqtt()


@router.on_event("shutdown")
async def shutdown():
    shutdown_mqtt()


# ── Pages ────────────────────────────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Show landing page - redirects to member view if logged in"""
    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")

    # Unified login: everyone goes to /member first
    if request.session.get("user"):
        return RedirectResponse("/member", status_code=302)

    # Not logged in - show landing page with login options
    return templates.TemplateResponse("landing.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render main dashboard - requires admin verification"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import is_admin_verified

    templates = Jinja2Templates(directory="templates")

    # Must be logged in
    if not request.session.get("user"):
        return RedirectResponse("/", status_code=302)

    # Must have admin verified
    if not is_admin_verified(request):
        return RedirectResponse("/member?admin_required=1", status_code=302)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "nav_active": "dashboard",
            "current_user": request.session.get("user"),
        },
    )


@router.get("/database", response_class=HTMLResponse)
async def database_page(request: Request):
    """Render database info page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth

    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "database.html",
        {
            "request": request,
            "nav_active": "devices",
            "current_user": request.session.get("user"),
        },
    )


@router.get("/devices/{device_id}", response_class=HTMLResponse)
async def device_detail_page(device_id: str, request: Request):
    """Render device detail page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth

    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "device-detail.html",
        {
            "request": request,
            "device_id": device_id,
            "nav_active": "devices",
            "current_user": request.session.get("user"),
        },
    )


# ── API ──────────────────────────────────────────────────────────────────────


@router.get("/api/database/stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """Get database file info and aggregate stats for the database page"""
    db_path = Path("core.db")
    try:
        size_bytes = db_path.stat().st_size
        if size_bytes < 1024:
            size_human = f"{size_bytes} B"
        elif size_bytes < 1024**2:
            size_human = f"{size_bytes / 1024:.1f} KB"
        else:
            size_human = f"{size_bytes / 1024**2:.1f} MB"
    except OSError:
        size_bytes = 0
        size_human = "Unknown"

    total_devices = db.query(Device).count()
    nfc_ok = db.query(Device).filter(Device.nfc_ok == 1).count()
    nfc_error = db.query(Device).filter(Device.nfc_ok == 0).count()
    nfc_unknown = total_devices - nfc_ok - nfc_error

    # online/offline based on last_seen within 2 minutes
    cutoff = datetime.utcnow() - timedelta(minutes=2)
    online = db.query(Device).filter(Device.last_seen >= cutoff).count()
    offline = total_devices - online

    oldest_device = db.query(func.min(Device.last_seen)).scalar()
    newest_device = db.query(func.max(Device.last_seen)).scalar()

    total_messages = db.query(MQTTMessage).count()
    topic_count = db.query(MQTTMessage.topic).distinct().count()
    oldest_message = db.query(func.min(MQTTMessage.timestamp)).scalar()
    newest_message = db.query(func.max(MQTTMessage.timestamp)).scalar()

    return {
        "database": {
            "file_path": str(db_path.resolve()),
            "size_human": size_human,
        },
        "devices": {
            "total": total_devices,
            "online": online,
            "offline": offline,
            "nfc_ok": nfc_ok,
            "nfc_error": nfc_error,
            "nfc_unknown": nfc_unknown,
        },
        "messages": {
            "total": total_messages,
            "topics": topic_count,
            "oldest": oldest_message.isoformat() if oldest_message else None,
            "newest": newest_message.isoformat() if newest_message else None,
        },
        "devices_oldest_seen": oldest_device.isoformat() if oldest_device else None,
        "devices_newest_seen": newest_device.isoformat() if newest_device else None,
    }


@router.get("/api/status")
async def get_status(db: Session = Depends(get_db)):
    """Get system status overview"""
    devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.status == "online").count()
    messages_24h = (
        db.query(MQTTMessage)
        .filter(MQTTMessage.timestamp >= datetime.utcnow() - timedelta(hours=24))
        .count()
    )
    total_messages = db.query(MQTTMessage).count()

    return {
        "devices_total": devices,
        "devices_online": online_devices,
        "messages_24h": messages_24h,
        "messages_total": total_messages,
        "status": "ok",
    }


@router.get("/api/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics for tiles"""
    # Count open Laufzettel (payment_method is None)
    from backend.laufzettel.db import get_db as get_laufzettel_db
    from backend.laufzettel.models import Laufzettel
    from backend.buchhaltung.db import SessionLocal as BuchhaltungSession
    from backend.buchhaltung.models import Spende

    laufzettel_db = next(get_laufzettel_db())
    try:
        open_laufzettel = (
            laufzettel_db.query(Laufzettel)
            .filter(Laufzettel.payment_method.is_(None))
            .count()
        )

        # Count unique member_id from open Laufzettel created today
        today = datetime.utcnow().date()
        members_today = (
            laufzettel_db.query(func.distinct(Laufzettel.member_id))
            .filter(
                Laufzettel.payment_method.is_(None),
                func.date(Laufzettel.created_at) == today,
                Laufzettel.member_id.isnot(None),
            )
            .count()
        )
    finally:
        laufzettel_db.close()

    # Count offline devices (last_seen > 2 minutes ago)
    cutoff = datetime.utcnow() - timedelta(minutes=2)
    offline_devices = db.query(Device).filter(Device.last_seen < cutoff).count()

    # Calculate Spenden for current month
    buchhaltung_db = BuchhaltungSession()
    try:
        current_month = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        next_month = (
            current_month.replace(month=current_month.month % 12 + 1)
            if current_month.month < 12
            else current_month.replace(year=current_month.year + 1, month=1)
        )
        spenden_current_month = (
            buchhaltung_db.query(func.sum(Spende.amount))
            .filter(Spende.date >= current_month, Spende.date < next_month)
            .scalar()
            or 0.0
        )
    finally:
        buchhaltung_db.close()

    # Get system status
    system_status = {
        "docs": await check_docs_status(),
        "zigbee": check_zigbee_status(),
        "databases": check_database_status(),
        "gdrive": check_gdrive_status(),
    }

    return {
        "open_laufzettel_count": open_laufzettel,
        "offline_devices_count": offline_devices,
        "spenden_current_month": spenden_current_month,
        "members_today": members_today,
        "system_status": system_status,
    }


@router.get("/api/devices")
async def get_devices(db: Session = Depends(get_db)):
    """List all known devices"""
    devices = db.query(Device).order_by(Device.last_seen.desc()).all()
    return [d.to_dict() for d in devices]


@router.get("/api/devices/{device_id}")
async def get_device(device_id: str, db: Session = Depends(get_db)):
    """Get single device details with topic counts and recent messages"""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    topic_counts = (
        db.query(MQTTMessage.topic, func.count(MQTTMessage.id).label("count"))
        .filter(MQTTMessage.topic.like(f"{device_id}/%"))
        .group_by(MQTTMessage.topic)
        .order_by(func.count(MQTTMessage.id).desc())
        .all()
    )

    recent_messages = (
        db.query(MQTTMessage)
        .filter(MQTTMessage.topic.like(f"{device_id}/%"))
        .order_by(MQTTMessage.timestamp.desc())
        .limit(100)
        .all()
    )

    return {
        "device": device.to_dict(),
        "topic_counts": [{"topic": t.topic, "count": t.count} for t in topic_counts],
        "recent_messages": [m.to_dict() for m in recent_messages],
    }


@router.delete("/api/devices/{device_id}")
async def delete_device(
    device_id: str, request: Request, db: Session = Depends(get_db)
):
    """Delete a device record"""
    from backend.auth.dependencies import is_admin_verified

    if not is_admin_verified(request):
        raise HTTPException(status_code=403, detail="Admin verification required")
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()
    return {"deleted": device_id}


@router.get("/api/messages")
async def get_messages(
    limit: int = 100, topic: Optional[str] = None, db: Session = Depends(get_db)
):
    """List recent MQTT messages"""
    q = db.query(MQTTMessage)
    if topic:
        q = q.filter(MQTTMessage.topic.like(f"%{topic}%"))
    messages = q.order_by(MQTTMessage.timestamp.desc()).limit(limit).all()
    return [m.to_dict() for m in messages]


@router.get("/api/messages/stats")
async def get_message_stats(db: Session = Depends(get_db)):
    """Get message statistics by topic prefix"""
    stats = (
        db.query(
            func.substr(
                MQTTMessage.topic, 1, func.instr(MQTTMessage.topic, "/") - 1
            ).label("prefix"),
            func.count(MQTTMessage.id).label("count"),
        )
        .filter(MQTTMessage.topic.like("%/%"))
        .group_by("prefix")
        .all()
    )

    return [{"prefix": s.prefix or "(root)", "count": s.count} for s in stats]


@router.get("/api/topics")
async def get_topics(db: Session = Depends(get_db)):
    """List all known MQTT topics"""
    topics = db.query(MQTTMessage.topic).distinct().all()
    return sorted([t.topic for t in topics])


@router.get("/api/scans")
async def get_scans(
    limit: int = 50, validated: Optional[bool] = None, db: Session = Depends(get_db)
):
    """List recent tag scans, enriched with member info"""
    q = db.query(TagScan)
    if validated is not None:
        q = q.filter(TagScan.validated == (1 if validated else 0))
    scans = q.order_by(TagScan.timestamp.desc()).limit(limit).all()
    results = [s.to_dict() for s in scans]

    # Enrich with member_id and member_name from members.db
    uids = {r["uid"] for r in results if r["uid"]}
    if uids:
        try:
            from backend.members.db import SessionLocal as MembersSession
            from backend.members.models import Mitglied, RFIDTag as MRFIDTag

            members_db = MembersSession()
            try:
                uid_to_member = {}
                for m in (
                    members_db.query(Mitglied).filter(Mitglied.nfc_uid.in_(uids)).all()
                ):
                    uid_to_member[m.nfc_uid] = {
                        "member_id": m.member_id,
                        "member_name": m.name,
                    }
                for tag in (
                    members_db.query(MRFIDTag)
                    .filter(MRFIDTag.uid.in_(uids - uid_to_member.keys()))
                    .all()
                ):
                    if tag.member_id:
                        m = (
                            members_db.query(Mitglied)
                            .filter(Mitglied.member_id == tag.member_id)
                            .first()
                        )
                        uid_to_member[tag.uid] = {
                            "member_id": tag.member_id,
                            "member_name": m.name if m else tag.owner_name,
                        }
            finally:
                members_db.close()
            for r in results:
                info = uid_to_member.get(r["uid"], {})
                r["member_id"] = info.get("member_id")
                r["member_name"] = info.get("member_name")
        except Exception:
            for r in results:
                r["member_id"] = None
                r["member_name"] = None

    return results


@router.get("/api/scans/stats")
async def get_scan_stats(db: Session = Depends(get_db)):
    """Get scan statistics"""
    total = db.query(TagScan).count()
    validated = db.query(TagScan).filter(TagScan.validated == 1).count()
    unknown = total - validated

    return {
        "total": total,
        "validated": validated,
        "unknown": unknown,
        "validation_rate": validated / total if total > 0 else 0,
    }


# ── Zigbee Devices API ───────────────────────────────────────────────────────


@router.get("/api/zigbee-devices")
async def get_zigbee_devices(db: Session = Depends(get_db)):
    """List all discovered Zigbee devices"""
    devices = db.query(ZigbeeDevice).order_by(ZigbeeDevice.last_seen.desc()).all()
    return [d.to_dict() for d in devices]


@router.get("/api/zigbee-devices/{ieee_address}")
async def get_zigbee_device(ieee_address: str, db: Session = Depends(get_db)):
    """Get single Zigbee device details by IEEE address"""
    device = (
        db.query(ZigbeeDevice).filter(ZigbeeDevice.ieee_address == ieee_address).first()
    )
    if not device:
        raise HTTPException(status_code=404, detail="Zigbee device not found")
    return device.to_dict()


@router.get("/api/zigbee-devices/{ieee_address}/messages")
async def get_zigbee_device_messages(
    ieee_address: str, limit: int = 50, db: Session = Depends(get_db)
):
    """Get recent MQTT messages for a specific Zigbee device"""
    # Search by IEEE address or friendly name in MQTT topics
    device = (
        db.query(ZigbeeDevice).filter(ZigbeeDevice.ieee_address == ieee_address).first()
    )
    if not device:
        raise HTTPException(status_code=404, detail="Zigbee device not found")

    # Build search terms: both IEEE and friendly name
    search_terms = [ieee_address]
    if device.friendly_name:
        search_terms.append(device.friendly_name)

    # Query messages that match any of the search terms in the topic
    q = db.query(MQTTMessage)
    filter_conditions = [
        MQTTMessage.topic.like(f"zigbee2mqtt/%{term}%") for term in search_terms
    ]
    if filter_conditions:
        from sqlalchemy import or_

        q = q.filter(or_(*filter_conditions))

    messages = q.order_by(MQTTMessage.timestamp.desc()).limit(limit).all()
    return [m.to_dict() for m in messages]


@router.get("/api/scans/stream")
async def scan_stream(request: Request):
    """SSE endpoint: streams NFC scan events to enrolled-reader listeners.
    Sends an initial config event with the current enrollment_reader_id,
    then pushes scan events until the client disconnects or 30 s elapse.
    """
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    entry = (queue, loop)
    scan_subscribers.append(entry)

    async def event_generator():
        try:
            # First event: send configured reader id so the client can filter
            reader_id = _app_config.ENROLLMENT_READER_ID
            yield f"event: config\ndata: {json.dumps({'enrollment_reader_id': reader_id})}\n\n"

            deadline = loop.time() + 30
            while True:
                if await request.is_disconnected():
                    break
                remaining = deadline - loop.time()
                if remaining <= 0:
                    yield f"event: timeout\ndata: {json.dumps({'message': 'timeout'})}\n\n"
                    break
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=min(remaining, 1.0)
                    )
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    continue
        finally:
            if entry in scan_subscribers:
                scan_subscribers.remove(entry)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/write-result")
async def get_write_result(
    device_id: str, request_id: str, db: Session = Depends(get_db)
):
    """Poll for NFC card write result published by PicoW to {device_id}/write_response"""
    topic = f"{device_id}/write_response"
    cutoff = datetime.utcnow() - timedelta(seconds=60)
    messages = (
        db.query(MQTTMessage)
        .filter(MQTTMessage.topic == topic, MQTTMessage.timestamp >= cutoff)
        .order_by(MQTTMessage.timestamp.desc())
        .limit(20)
        .all()
    )
    import json as _json

    for msg in messages:
        try:
            payload = _json.loads(msg.payload)
            if payload.get("request_id") == request_id:
                return {
                    "found": True,
                    "success": payload.get("success"),
                    "error": payload.get("error"),
                    "uid": payload.get("uid"),
                }
        except Exception:
            continue
    return {"found": False}


class EnrollmentReaderUpdate(BaseModel):
    enrollment_reader_id: str


class PaymentReaderUpdate(BaseModel):
    payment_reader_id: str


class CardWriterUpdate(BaseModel):
    card_writer_id: str


@router.get("/api/settings/enrollment-reader")
async def get_enrollment_reader(db: Session = Depends(get_db)):
    """Get the current enrollment reader device ID and list of known devices."""
    devices = db.query(Device).order_by(Device.last_seen.desc()).all()
    return {
        "enrollment_reader_id": _app_config.ENROLLMENT_READER_ID,
        "devices": [{"id": d.device_id, "name": d.name or d.device_id} for d in devices],
    }


@router.put("/api/settings/enrollment-reader")
async def set_enrollment_reader(data: EnrollmentReaderUpdate):
    """Update the enrollment reader device ID in memory and persist to config.json."""
    new_id = data.enrollment_reader_id.strip()
    # Update in-memory config
    _app_config.ENROLLMENT_READER_ID = new_id
    # Persist to config/config.json
    cfg_path = Path("config/config.json")
    try:
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        cfg["enrollment_reader_id"] = new_id
        cfg_path.write_text(json.dumps(cfg, indent=4, ensure_ascii=False))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist config: {exc}")
    return {"enrollment_reader_id": new_id}


@router.get("/api/settings/payment-reader")
async def get_payment_reader(db: Session = Depends(get_db)):
    """Get the current payment reader device ID and list of known devices."""
    devices = db.query(Device).order_by(Device.last_seen.desc()).all()
    return {
        "payment_reader_id": _app_config.PAYMENT_READER_ID,
        "devices": [{"id": d.device_id, "name": d.name or d.device_id} for d in devices],
    }


@router.put("/api/settings/payment-reader")
async def set_payment_reader(data: PaymentReaderUpdate):
    """Update the payment reader device ID in memory and persist to config.json."""
    new_id = data.payment_reader_id.strip()
    _app_config.PAYMENT_READER_ID = new_id
    cfg_path = Path("config/config.json")
    try:
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        cfg["payment_reader_id"] = new_id
        cfg_path.write_text(json.dumps(cfg, indent=4, ensure_ascii=False))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist config: {exc}")
    return {"payment_reader_id": new_id}


@router.get("/api/settings/card-writer")
async def get_card_writer(db: Session = Depends(get_db)):
    """Get the current card writer device ID and list of known devices."""
    devices = db.query(Device).order_by(Device.last_seen.desc()).all()
    return {
        "card_writer_id": _app_config.CARD_WRITER_ID,
        "devices": [{"id": d.device_id, "name": d.name or d.device_id} for d in devices],
    }


@router.put("/api/settings/card-writer")
async def set_card_writer(data: CardWriterUpdate):
    """Update the card writer device ID in memory and persist to config.json."""
    new_id = data.card_writer_id.strip()
    _app_config.CARD_WRITER_ID = new_id
    cfg_path = Path("config/config.json")
    try:
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        cfg["card_writer_id"] = new_id
        cfg_path.write_text(json.dumps(cfg, indent=4, ensure_ascii=False))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist config: {exc}")
    return {"card_writer_id": new_id}


@router.get("/api/scans/payment-stream")
async def payment_scan_stream(request: Request):
    """SSE endpoint: streams NFC scan events filtered by payment_reader_id.
    Same mechanism as /api/scans/stream but for the payment checkout reader.
    """
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    entry = (queue, loop)
    scan_subscribers.append(entry)

    async def event_generator():
        try:
            reader_id = _app_config.PAYMENT_READER_ID
            yield f"event: config\ndata: {json.dumps({'payment_reader_id': reader_id})}\n\n"

            deadline = loop.time() + 120
            while True:
                if await request.is_disconnected():
                    break
                remaining = deadline - loop.time()
                if remaining <= 0:
                    yield f"event: timeout\ndata: {json.dumps({'message': 'timeout'})}\n\n"
                    break
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=min(remaining, 1.0)
                    )
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    continue
        finally:
            if entry in scan_subscribers:
                scan_subscribers.remove(entry)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

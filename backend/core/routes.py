"""Core routes - devices, messages, status, dashboard"""

import asyncio
import json
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
    
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/database", response_class=HTMLResponse)
async def database_page(request: Request):
    """Render database info page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth
    
    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("database.html", {"request": request})


@router.get("/devices/{device_id}", response_class=HTMLResponse)
async def device_detail_page(device_id: str, request: Request):
    """Render device detail page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth

    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("device-detail.html", {"request": request, "device_id": device_id})


# ── API ──────────────────────────────────────────────────────────────────────

@router.get("/api/status")
async def get_status(db: Session = Depends(get_db)):
    """Get system status overview"""
    devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.status == "online").count()
    messages_24h = db.query(MQTTMessage).filter(
        MQTTMessage.timestamp >= datetime.utcnow() - timedelta(hours=24)
    ).count()
    total_messages = db.query(MQTTMessage).count()
    
    return {
        "devices_total": devices,
        "devices_online": online_devices,
        "messages_24h": messages_24h,
        "messages_total": total_messages,
        "status": "ok",
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


@router.get("/api/messages")
async def get_messages(
    limit: int = 100,
    topic: Optional[str] = None,
    db: Session = Depends(get_db)
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
    stats = db.query(
        func.substr(MQTTMessage.topic, 1, func.instr(MQTTMessage.topic, "/") - 1).label("prefix"),
        func.count(MQTTMessage.id).label("count")
    ).filter(MQTTMessage.topic.like("%/%")).group_by("prefix").all()
    
    return [{"prefix": s.prefix or "(root)", "count": s.count} for s in stats]


@router.get("/api/topics")
async def get_topics(db: Session = Depends(get_db)):
    """List all known MQTT topics"""
    topics = db.query(MQTTMessage.topic).distinct().all()
    return sorted([t.topic for t in topics])


@router.get("/api/scans")
async def get_scans(
    limit: int = 50,
    validated: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List recent tag scans"""
    q = db.query(TagScan)
    if validated is not None:
        q = q.filter(TagScan.validated == (1 if validated else 0))
    scans = q.order_by(TagScan.timestamp.desc()).limit(limit).all()
    return [s.to_dict() for s in scans]


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
    device = db.query(ZigbeeDevice).filter(
        ZigbeeDevice.ieee_address == ieee_address
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Zigbee device not found")
    return device.to_dict()


@router.get("/api/zigbee-devices/{ieee_address}/messages")
async def get_zigbee_device_messages(
    ieee_address: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get recent MQTT messages for a specific Zigbee device"""
    # Search by IEEE address or friendly name in MQTT topics
    device = db.query(ZigbeeDevice).filter(
        ZigbeeDevice.ieee_address == ieee_address
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Zigbee device not found")

    # Build search terms: both IEEE and friendly name
    search_terms = [ieee_address]
    if device.friendly_name:
        search_terms.append(device.friendly_name)

    # Query messages that match any of the search terms in the topic
    q = db.query(MQTTMessage)
    filter_conditions = [
        MQTTMessage.topic.like(f"zigbee2mqtt/%{term}%")
        for term in search_terms
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
                    event = await asyncio.wait_for(queue.get(), timeout=min(remaining, 1.0))
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


class EnrollmentReaderUpdate(BaseModel):
    enrollment_reader_id: str


@router.get("/api/settings/enrollment-reader")
async def get_enrollment_reader(db: Session = Depends(get_db)):
    """Get the current enrollment reader device ID and list of known devices."""
    devices = db.query(Device).order_by(Device.last_seen.desc()).all()
    return {
        "enrollment_reader_id": _app_config.ENROLLMENT_READER_ID,
        "devices": [d.device_id for d in devices],
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

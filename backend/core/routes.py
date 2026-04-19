"""Core routes - devices, messages, status, dashboard"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .models import MQTTMessage, Device, TagScan
from .mqtt import init_mqtt, shutdown_mqtt

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
    """Show landing page with RFID login or redirect to appropriate dashboard"""
    from backend.auth.dependencies import check_auth
    from backend.auth.db import SessionLocal
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="templates")
    
    if check_auth(request):
        # Verify user actually exists in DB
        username = request.session.get("user")
        db = SessionLocal()
        try:
            from backend.auth.models import User
            user = db.query(User).filter(User.username == username).first()
            if user:
                # User exists - redirect based on role
                role = request.session.get("role", "member")
                if role == "admin":
                    return RedirectResponse("/dashboard", status_code=302)
                else:
                    return RedirectResponse("/member", status_code=302)
            else:
                # Session has invalid user - clear it
                request.session.clear()
        finally:
            db.close()
    
    # Not logged in - show landing page with RFID scan
    return templates.TemplateResponse("landing.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render main dashboard"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth
    
    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/database", response_class=HTMLResponse)
async def database_page(request: Request):
    """Render database info page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth
    
    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("database.html", {"request": request})


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
    """Get single device details"""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device.to_dict()


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

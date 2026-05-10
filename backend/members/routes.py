"""Members routes - API and pages for Mitglied and RFIDTag"""

from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .models import Mitglied, RFIDTag
from .easyverein import sync_members_from_easyverein, get_sync_status
from .signature import generate_card_signature


class CardWriteRequest(BaseModel):
    device_id: Optional[str] = (
        None  # PicoW device ID; falls back to CARD_WRITER_ID config
    )
    uid: str  # Expected UID to write to (for verification)


router = APIRouter()


class MitgliedCreate(BaseModel):
    member_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str = "active"
    joined_date: Optional[str] = None
    notes: Optional[str] = None
    nfc_uid: Optional[str] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None


class MitgliedUpdate(BaseModel):
    member_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    joined_date: Optional[str] = None
    notes: Optional[str] = None
    nfc_uid: Optional[str] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None


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


@router.on_event("startup")
async def startup():
    init_db()


# ── Pages ───────────────────────────────────────────────────────────────────


@router.get("/mitglieder", response_class=HTMLResponse)
async def mitglieder_page(request: Request):
    """Render member database page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth

    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "mitglieder.html",
        {
            "request": request,
            "nav_active": "mitglieder",
            "current_user": request.session.get("user"),
        },
    )


@router.get("/tags", response_class=HTMLResponse)
async def tags_page(request: Request):
    """Render RFID tag management page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth

    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "tags.html",
        {
            "request": request,
            "nav_active": "tags",
            "current_user": request.session.get("user"),
        },
    )


# ── Mitglied API ──────────────────────────────────────────────────────────────


@router.get("/api/mitglieder")
async def get_mitglieder(
    search: str = None, status: str = None, db: Session = Depends(get_db)
):
    """List all members, optionally filtered (only active members returned)"""
    q = db.query(Mitglied).filter(Mitglied.status == "active")
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Mitglied.name.ilike(like))
            | (Mitglied.member_id.ilike(like))
            | (Mitglied.email.ilike(like))
        )
    # status filter is ignored since we only return active members
    return [m.to_dict() for m in q.order_by(Mitglied.name).all()]


@router.get("/api/mitglieder/{mitglied_id}")
async def get_mitglied_details(mitglied_id: int, db: Session = Depends(get_db)):
    """Get detailed information for a single member"""
    m = db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return m.to_dict()


@router.post("/api/mitglieder")
async def create_mitglied(data: MitgliedCreate, db: Session = Depends(get_db)):
    """Create a new member"""
    existing = db.query(Mitglied).filter(Mitglied.member_id == data.member_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="member_id already exists")
    # Check if login_username already exists (if provided)
    if data.login_username:
        existing_login = (
            db.query(Mitglied)
            .filter(Mitglied.login_username == data.login_username)
            .first()
        )
        if existing_login:
            raise HTTPException(status_code=400, detail="login_username already exists")
    nfc_uid = data.nfc_uid.upper() if data.nfc_uid else None
    if nfc_uid:
        clash = db.query(Mitglied).filter(Mitglied.nfc_uid == nfc_uid).first()
        if clash:
            raise HTTPException(
                status_code=400, detail="nfc_uid already assigned to another member"
            )
    from datetime import date as dt_date
    from backend.auth.dependencies import get_password_hash

    m = Mitglied(
        member_id=data.member_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
        status=data.status or "active",
        joined_date=dt_date.fromisoformat(data.joined_date)
        if data.joined_date
        else None,
        notes=data.notes,
        nfc_uid=nfc_uid,
        login_username=data.login_username,
        login_password_hash=get_password_hash(data.login_password)
        if data.login_password
        else None,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m.to_dict()


@router.put("/api/mitglieder/{mitglied_id}")
async def update_mitglied(
    mitglied_id: int, data: MitgliedUpdate, db: Session = Depends(get_db)
):
    """Update a member"""
    m = db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    if data.member_id is not None:
        clash = (
            db.query(Mitglied)
            .filter(Mitglied.member_id == data.member_id, Mitglied.id != mitglied_id)
            .first()
        )
        if clash:
            raise HTTPException(status_code=400, detail="member_id already exists")
        m.member_id = data.member_id
    if data.name is not None:
        m.name = data.name
    if data.email is not None:
        m.email = data.email
    if data.phone is not None:
        m.phone = data.phone
    if data.status is not None:
        m.status = data.status
    if data.joined_date is not None:
        from datetime import date as dt_date

        m.joined_date = (
            dt_date.fromisoformat(data.joined_date) if data.joined_date else None
        )
    if data.notes is not None:
        m.notes = data.notes
    if data.nfc_uid is not None:
        nfc_uid = data.nfc_uid.upper() if data.nfc_uid else None
        if nfc_uid:
            clash = (
                db.query(Mitglied)
                .filter(Mitglied.nfc_uid == nfc_uid, Mitglied.id != mitglied_id)
                .first()
            )
            if clash:
                raise HTTPException(
                    status_code=400, detail="nfc_uid already assigned to another member"
                )
        m.nfc_uid = nfc_uid
    # Handle login credentials
    if data.login_username is not None:
        # Check if username already taken by another member
        if data.login_username != m.login_username:
            existing = (
                db.query(Mitglied)
                .filter(
                    Mitglied.login_username == data.login_username,
                    Mitglied.id != mitglied_id,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=400, detail="login_username already exists"
                )
        m.login_username = data.login_username if data.login_username else None
    if data.login_password is not None:
        from backend.auth.dependencies import get_password_hash

        m.login_password_hash = (
            get_password_hash(data.login_password) if data.login_password else None
        )
    db.commit()
    db.refresh(m)
    return m.to_dict()


# ── easyVerein Sync API (must be before /{mitglied_id}) ───────────────────────


@router.get("/api/mitglieder/sync-status")
async def get_easyverein_sync_status(request: Request):
    """Get the last easyVerein sync status"""
    from backend.auth.dependencies import check_auth

    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_sync_status()


@router.post("/api/mitglieder/sync")
async def trigger_easyverein_sync(request: Request):
    """Manually trigger easyVerein sync (admin only)"""
    from backend.auth.dependencies import is_admin_verified

    if not is_admin_verified(request):
        raise HTTPException(status_code=403, detail="Admin verification required")
    result = await sync_members_from_easyverein()
    return result


@router.get("/api/mitglieder/{mitglied_id}")
async def get_mitglied(mitglied_id: int, db: Session = Depends(get_db)):
    """Get a single member by ID"""
    m = db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return m.to_dict()


@router.delete("/api/mitglieder/{mitglied_id}")
async def delete_mitglied(mitglied_id: int, db: Session = Depends(get_db)):
    """Delete a member"""
    m = db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(m)
    db.commit()
    return {"success": True}


# ── RFID Tag API ───────────────────────────────────────────────────────────────


@router.get("/api/tags")
async def get_tags(db: Session = Depends(get_db)):
    """List all registered RFID tags — merges RFIDTag table with Mitglied.nfc_uid enrollments."""
    tags = db.query(RFIDTag).order_by(RFIDTag.created_at.desc()).all()
    result = [t.to_dict() for t in tags]
    known_uids = {t.uid for t in tags}

    # Include members enrolled via the Mitglieder UI (Mitglied.nfc_uid) not already in RFIDTag
    enrolled = db.query(Mitglied).filter(Mitglied.nfc_uid.isnot(None)).all()
    for m in enrolled:
        uid = m.nfc_uid.upper() if m.nfc_uid else None
        if uid and uid not in known_uids:
            result.append(
                {
                    "id": None,
                    "uid": uid,
                    "member_id": m.member_id,
                    "owner_name": m.name,
                    "owner_email": m.email,
                    "notes": None,
                    "active": 1,
                    "is_admin": False,
                    "created_at": None,
                    "source": "mitglied",
                }
            )
    return result


@router.get("/api/tags/{uid}")
async def get_tag(uid: str, db: Session = Depends(get_db)):
    """Get a single tag by UID"""
    tag = db.query(RFIDTag).filter(RFIDTag.uid == uid.upper()).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag.to_dict()


@router.post("/api/tags")
async def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    """Register a new RFID tag"""
    uid = data.uid.upper()
    existing = db.query(RFIDTag).filter(RFIDTag.uid == uid).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag already registered")
    new_tag = RFIDTag(
        uid=uid,
        owner_name=data.owner_name,
        member_id=data.member_id or None,
        owner_email=data.owner_email or None,
        notes=data.notes or None,
        active=1 if data.active else 0,
    )
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    return new_tag.to_dict()


@router.put("/api/tags/{uid}")
async def update_tag(uid: str, data: TagUpdate, db: Session = Depends(get_db)):
    """Update a registered tag"""
    tag = db.query(RFIDTag).filter(RFIDTag.uid == uid.upper()).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if data.owner_name is not None:
        tag.owner_name = data.owner_name
    if data.member_id is not None:
        tag.member_id = data.member_id or None
    if data.owner_email is not None:
        tag.owner_email = data.owner_email or None
    if data.notes is not None:
        tag.notes = data.notes or None
    if data.active is not None:
        tag.active = 1 if data.active else 0
    db.commit()
    db.refresh(tag)
    return tag.to_dict()


@router.delete("/api/tags/{uid}")
async def delete_tag(uid: str, db: Session = Depends(get_db)):
    """Delete a registered tag"""
    tag = db.query(RFIDTag).filter(RFIDTag.uid == uid.upper()).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(tag)
    db.commit()
    return {"success": True}


# ── Card Enrollment (Write to NFC) ───────────────────────────────────────────


@router.post("/api/mitglieder/{mitglied_id}/enroll-card")
async def enroll_card(
    mitglied_id: int,
    req: CardWriteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Trigger NFC card enrollment - writes member data to card via PicoW.

    The PicoW must have a pending write job stored. When the member presents
    their card, the data will be written and verified.
    """
    from backend.auth.dependencies import check_auth

    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get member
    m = db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    # Normalize UID
    uid = req.uid.upper().replace(":", "").replace("-", "")

    # Generate signature binding UID to member
    signature = generate_card_signature(m.member_id, uid, m.name)

    # Send write command to PicoW
    from backend.core.mqtt import send_card_write_command
    from backend import config as _cfg
    import uuid

    device_id = req.device_id or _cfg.CARD_WRITER_ID
    if not device_id:
        raise HTTPException(
            status_code=400,
            detail="No card writer device configured. Set card_writer_id in Devices settings.",
        )

    request_id = str(uuid.uuid4())[:8]
    success = send_card_write_command(
        device_id=device_id,
        member_id=m.member_id,
        name=m.name,
        email=m.email or "",
        signature=signature,
        request_id=request_id,
    )

    if not success:
        raise HTTPException(status_code=503, detail="Failed to send command to device")

    return {
        "success": True,
        "message": f"Present card to {device_id} within 30 seconds",
        "request_id": request_id,
        "device_id": device_id,
        "member_id": m.member_id,
        "uid": req.uid,
    }

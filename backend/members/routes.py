"""Members routes - API and pages for Mitglied and RFIDTag"""

import logging
from datetime import datetime as dt_datetime
from datetime import timezone as dt_timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .easyverein import get_sync_status, sync_members_from_easyverein
from .models import DevicePermission, Mitglied, RFIDTag
from .signature import generate_card_signature


class CardWriteRequest(BaseModel):
    device_id: Optional[str] = (
        None  # PicoW device ID; falls back to CARD_WRITER_ID config
    )
    uid: str  # Expected UID to write to (for verification)


router = APIRouter()
logger = logging.getLogger(__name__)


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
    sync_locked: Optional[bool] = None


class MemberRegistrationRequest(BaseModel):
    # Step 1 - Personal
    salutation: Optional[str] = None
    first_name: str
    family_name: str
    email: str
    date_of_birth: Optional[str] = None
    mobile_phone: Optional[str] = None
    private_phone: Optional[str] = None
    # Step 2 - Address
    street: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Deutschland"
    # Step 3 - Membership (free-entry amount, 0 allowed)
    payment_amount: Optional[float] = None
    payment_interval_months: Optional[int] = None
    # Step 4 - Payment (SEPA only; skipped when payment_amount == 0)
    method_of_payment: Optional[int] = None
    iban: Optional[str] = None
    # Consent
    privacy_accepted: bool = False


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


class ApiKeyUpdate(BaseModel):
    api_key: str
    expires_at: str  # YYYY-MM-DD


class DevicePermissionCreate(BaseModel):
    device_id: str  # device_id from core.db, or "*" for all devices


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
    from datetime import date

    import backend.config as _config

    expires_str = _config.EASYVEREIN_KEY_EXPIRES_AT
    days_left = None
    if expires_str:
        try:
            days_left = (date.fromisoformat(expires_str) - date.today()).days
        except ValueError:
            pass
    return templates.TemplateResponse(
        "mitglieder.html",
        {
            "request": request,
            "nav_active": "mitglieder",
            "current_user": request.session.get("user"),
            "ev_key_expires_at": expires_str,
            "ev_key_days_left": days_left,
            "ev_renew_url": f"https://easyverein.com/app/{_config.EASYVEREIN_ORG_ID}/setting/api-key"
            if _config.EASYVEREIN_ORG_ID
            else "https://easyverein.com",
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


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Public member registration form"""
    from fastapi.templating import Jinja2Templates

    from backend.config import EASYVEREIN_API_KEY, MEMBERSHIP_GROUPS

    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "membership_groups": MEMBERSHIP_GROUPS,
            "easyverein_configured": bool(EASYVEREIN_API_KEY),
        },
    )


@router.post("/api/register")
async def register_member(
    data: MemberRegistrationRequest, db: Session = Depends(get_db)
):
    """Public endpoint: submit a new member application.

    Creates an application in easyVerein (if configured) and a local inactive Mitglied.
    """
    from backend.config import EASYVEREIN_API_KEY
    from backend.members.easyverein import create_member_application

    if not data.privacy_accepted:
        raise HTTPException(
            status_code=400, detail="Datenschutzerklärung muss akzeptiert werden"
        )

    if not data.first_name.strip() or not data.family_name.strip():
        raise HTTPException(
            status_code=422, detail="Vor- und Nachname sind erforderlich"
        )

    if not data.email.strip():
        raise HTTPException(status_code=422, detail="E-Mail-Adresse ist erforderlich")

    # Check for duplicate email
    existing = (
        db.query(Mitglied).filter(Mitglied.email == data.email.lower().strip()).first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Diese E-Mail-Adresse ist bereits registriert"
        )

    full_name = f"{data.first_name.strip()} {data.family_name.strip()}"
    member_id: Optional[str] = None
    ev_warning: Optional[str] = None

    if EASYVEREIN_API_KEY:
        try:
            ev_result = await create_member_application(data.model_dump())
            membership_number = ev_result.get("membership_number")
            if membership_number:
                member_id = str(membership_number)
        except Exception as e:
            logger.warning(
                f"easyVerein registration failed, creating local-only record: {e}"
            )
            ev_warning = str(e)

    if not member_id:
        # Local-only fallback: generate a placeholder ID
        ts = int(dt_datetime.now(dt_timezone.utc).timestamp())
        member_id = f"REG-{ts}"

    # Avoid member_id collision — use a fresh timestamp suffix if the ID is taken
    clash = db.query(Mitglied).filter(Mitglied.member_id == member_id).first()
    if clash:
        ts = int(dt_datetime.now(dt_timezone.utc).timestamp() * 1000) % 1_000_000
        member_id = f"REG-{ts}"

    new_member = Mitglied(
        member_id=member_id,
        name=full_name,
        email=data.email.lower().strip(),
        phone=data.mobile_phone or data.private_phone,
        status="inactive",
        joined_date=None,
        notes=(
            f"Antrag über Webformular. Zahlung: {data.method_of_payment}, "
            f"Betrag: {data.payment_amount}€/{data.payment_interval_months}Mo"
        ),
    )
    db.add(new_member)
    db.commit()

    response: dict = {"success": True, "message": "Antrag erfolgreich eingereicht"}
    if ev_warning:
        response["warning"] = (
            "Antrag lokal gespeichert; easyVerein-Übertragung fehlgeschlagen"
        )
    return response


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
    # Any admin edit locks the member out of easyVerein sync to preserve local changes
    # (unless sync_locked is explicitly being set to False to re-enable sync)
    if data.sync_locked is None:
        m.sync_locked = True
    else:
        m.sync_locked = data.sync_locked
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


@router.get("/api/mitglieder/key-status")
async def get_key_status(request: Request):
    """Return current easyVerein API key expiry info."""
    from datetime import date as _date

    import backend.config as _config
    from backend.auth.dependencies import check_auth

    if not check_auth(request):
        from fastapi.responses import JSONResponse

        return JSONResponse({"error": "unauthorized"}, status_code=401)
    expires_str = _config.EASYVEREIN_KEY_EXPIRES_AT
    days_left = None
    if expires_str:
        try:
            days_left = (_date.fromisoformat(expires_str) - _date.today()).days
        except ValueError:
            pass
    return {
        "expires_at": expires_str,
        "days_left": days_left,
        "renew_url": f"https://easyverein.com/app/{_config.EASYVEREIN_ORG_ID}/setting/api-key"
        if _config.EASYVEREIN_ORG_ID
        else "https://easyverein.com",
    }


@router.post("/api/mitglieder/update-api-key")
async def update_api_key(body: ApiKeyUpdate, request: Request):
    """Update the easyVerein API key and expiry date in config and in-memory."""
    import backend.config as _config
    import backend.members.easyverein as _ev
    from backend.auth.dependencies import is_admin_verified

    if not is_admin_verified(request):
        raise HTTPException(status_code=403, detail="Admin-Verifizierung erforderlich")
    if not body.api_key.strip():
        raise HTTPException(
            status_code=400, detail="API-Schlüssel darf nicht leer sein"
        )
    # Validate date format
    try:
        from datetime import date as _date

        _date.fromisoformat(body.expires_at)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Ungültiges Datum (erwartet YYYY-MM-DD)"
        )
    # Persist to config.json and update module-level vars
    _config.update_config(
        {
            "easyverein_api_key": body.api_key.strip(),
            "easyverein_key_expires_at": body.expires_at,
        }
    )
    # Also update the easyverein module's own binding (it imported the constant directly)
    _ev.EASYVEREIN_API_KEY = body.api_key.strip()
    return {"ok": True, "expires_at": body.expires_at}


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


# ── Device Permission API ───────────────────────────────────────────────────────


@router.get("/api/mitglieder/{mitglied_id}/permissions")
async def get_member_permissions(mitglied_id: int, db: Session = Depends(get_db)):
    """Get all device permissions for a member"""
    m = db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    permissions = (
        db.query(DevicePermission)
        .filter(DevicePermission.member_id == mitglied_id)
        .all()
    )

    return [
        {
            "id": p.id,
            "device_id": p.device_id,
            "granted_at": p.granted_at.isoformat() if p.granted_at else None,
        }
        for p in permissions
    ]


@router.post("/api/mitglieder/{mitglied_id}/permissions")
async def add_member_permission(
    mitglied_id: int, permission: DevicePermissionCreate, db: Session = Depends(get_db)
):
    """Add a device permission for a member"""
    m = db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    # Check if permission already exists
    existing = (
        db.query(DevicePermission)
        .filter(
            DevicePermission.member_id == mitglied_id,
            DevicePermission.device_id == permission.device_id,
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Permission already exists")

    new_permission = DevicePermission(
        member_id=mitglied_id,
        device_id=permission.device_id,
        granted_at=dt_datetime.now(dt_timezone.utc),
    )
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)

    return {
        "id": new_permission.id,
        "device_id": new_permission.device_id,
        "granted_at": new_permission.granted_at.isoformat(),
    }


@router.delete("/api/mitglieder/{mitglied_id}/permissions/{permission_id}")
async def delete_member_permission(
    mitglied_id: int, permission_id: int, db: Session = Depends(get_db)
):
    """Delete a device permission for a member"""
    permission = (
        db.query(DevicePermission)
        .filter(
            DevicePermission.id == permission_id,
            DevicePermission.member_id == mitglied_id,
        )
        .first()
    )

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    db.delete(permission)
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
    import uuid

    from backend import config as _cfg
    from backend.core.mqtt import send_card_write_command
    from backend.members.signature import get_mifare_sector_key

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
        sector_key=get_mifare_sector_key(),
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


@router.post("/api/mitglieder/{mitglied_id}/provision-login")
async def provision_login(
    mitglied_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Set login credentials for a member if they don't have them yet.

    Username is derived from the member's email address. Password defaults to
    the makerspace standard ("H3cke"). Idempotent — returns current state if
    credentials already exist.
    """
    from backend.auth.dependencies import check_auth, get_password_hash

    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")

    m = db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    if m.login_username:
        return {
            "success": True,
            "login_username": m.login_username,
            "provisioned": False,
        }

    # Derive username: use email if available, else member_id-based fallback
    base = (m.email or f"mitglied_{m.member_id}").lower().strip()
    username = base
    # Ensure uniqueness
    suffix = 1
    while (
        db.query(Mitglied)
        .filter(Mitglied.login_username == username, Mitglied.id != mitglied_id)
        .first()
    ):
        username = f"{base}_{suffix}"
        suffix += 1

    m.login_username = username
    m.login_password_hash = get_password_hash("H3cke")
    db.commit()
    logger.info("Provisioned login for member id=%s username=%r", mitglied_id, username)
    return {"success": True, "login_username": username, "provisioned": True}

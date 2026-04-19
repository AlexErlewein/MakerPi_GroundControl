"""Members routes - API and pages for Mitglied and RFIDTag"""

from typing import Optional
from fastapi import APIRouter, Request, Query, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .models import Mitglied, RFIDTag

router = APIRouter()


class MitgliedCreate(BaseModel):
    member_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str = "active"
    joined_date: Optional[str] = None
    notes: Optional[str] = None


class MitgliedUpdate(BaseModel):
    member_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    joined_date: Optional[str] = None
    notes: Optional[str] = None


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
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("mitglieder.html", {"request": request})


@router.get("/tags", response_class=HTMLResponse)
async def tags_page(request: Request):
    """Render RFID tag management page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth
    
    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("tags.html", {"request": request})


# ── Mitglied API ──────────────────────────────────────────────────────────────

@router.get("/api/mitglieder")
async def get_mitglieder(search: str = None, status: str = None, db: Session = Depends(get_db)):
    """List all members, optionally filtered"""
    q = db.query(Mitglied)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Mitglied.name.ilike(like)) |
            (Mitglied.member_id.ilike(like)) |
            (Mitglied.email.ilike(like))
        )
    if status:
        q = q.filter(Mitglied.status == status)
    return [m.to_dict() for m in q.order_by(Mitglied.name).all()]


@router.post("/api/mitglieder")
async def create_mitglied(data: MitgliedCreate, db: Session = Depends(get_db)):
    """Create a new member"""
    existing = db.query(Mitglied).filter(Mitglied.member_id == data.member_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="member_id already exists")
    from datetime import date as dt_date
    m = Mitglied(
        member_id=data.member_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
        status=data.status or "active",
        joined_date=dt_date.fromisoformat(data.joined_date) if data.joined_date else None,
        notes=data.notes,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m.to_dict()


@router.put("/api/mitglieder/{mitglied_id}")
async def update_mitglied(mitglied_id: int, data: MitgliedUpdate, db: Session = Depends(get_db)):
    """Update a member"""
    m = db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    if data.member_id is not None:
        clash = db.query(Mitglied).filter(
            Mitglied.member_id == data.member_id, Mitglied.id != mitglied_id
        ).first()
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
        m.joined_date = dt_date.fromisoformat(data.joined_date) if data.joined_date else None
    if data.notes is not None:
        m.notes = data.notes
    db.commit()
    db.refresh(m)
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
    """List all registered RFID tags"""
    tags = db.query(RFIDTag).order_by(RFIDTag.created_at.desc()).all()
    return [t.to_dict() for t in tags]


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

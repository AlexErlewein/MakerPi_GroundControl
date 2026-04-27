"""Member routes - member-only access to own laufzettel"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

import logging

from backend.auth.db import get_db as get_auth_db
from backend.auth.models import User
from backend.laufzettel.db import get_db as get_laufzettel_db
from backend.laufzettel.models import Laufzettel, LaufzettelMaterial
from backend.members.db import get_db as get_members_db
from backend.members.models import Mitglied, RFIDTag
from backend.catalog.db import get_db as get_catalog_db
from backend.catalog.models import MaterialVariante, MaterialKategorie

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")


def require_member(request: Request, db: Session = Depends(get_auth_db)):
    """Check if user is logged in as member or admin"""
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not authenticated")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(401, "User not found")
    
    if user.role not in ["admin", "member"]:
        raise HTTPException(403, "Access denied")
    
    return user


@router.get("/member")
async def member_dashboard(request: Request, db: Session = Depends(get_auth_db)):
    """Member dashboard - redirects to their laufzettel list"""
    # Check auth manually and redirect to login if not authenticated
    username = request.session.get("user")
    if not username:
        return RedirectResponse("/", status_code=302)
    
    user = db.query(User).filter(User.username == username).first()
    if not user or user.role not in ["admin", "member"]:
        return RedirectResponse("/", status_code=302)
    
    return RedirectResponse("/member/laufzettel", status_code=302)


@router.get("/member/laufzettel")
async def member_laufzettel_list(
    request: Request,
    db: Session = Depends(get_laufzettel_db),
    auth_db: Session = Depends(get_auth_db)
):
    """Show member's own laufzettel"""
    # Check auth manually and redirect to login if not authenticated
    username = request.session.get("user")
    if not username:
        return RedirectResponse("/", status_code=302)
    
    user = auth_db.query(User).filter(User.username == username).first()
    if not user or user.role not in ["admin", "member"]:
        return RedirectResponse("/", status_code=302)
    
    # Get laufzettel for this member
    if user.mitglied_id:
        # Primary: find by mitglied_id (DB FK)
        laufzettel = db.query(Laufzettel).filter(
            Laufzettel.mitglied_id == user.mitglied_id
        ).order_by(Laufzettel.created_at.desc()).all()
        # Fallback: also find uid-based entries (older records without mitglied_id)
        # Look up the member's nfc_uid and query by uid
        from backend.members.db import get_db as get_members_db_fn
        members_db = next(get_members_db_fn())
        try:
            from backend.members.models import Mitglied as _Mitglied
            mitglied = members_db.query(_Mitglied).filter(
                _Mitglied.id == user.mitglied_id
            ).first()
            if mitglied and mitglied.nfc_uid:
                uid_laufzettel = db.query(Laufzettel).filter(
                    Laufzettel.uid == mitglied.nfc_uid,
                    Laufzettel.mitglied_id.is_(None),
                ).order_by(Laufzettel.created_at.desc()).all()
                # Merge and deduplicate by id
                seen = {lz.id for lz in laufzettel}
                for lz in uid_laufzettel:
                    if lz.id not in seen:
                        laufzettel.append(lz)
                        seen.add(lz.id)
                laufzettel.sort(key=lambda lz: lz.created_at or lz.date, reverse=True)
        finally:
            members_db.close()
    else:
        # Admin without mitglied_id sees empty list
        laufzettel = []
    
    return templates.TemplateResponse(
        "member-laufzettel-list.html",
        {
            "request": request,
            "laufzettel": laufzettel,
            "user": user,
        },
    )


@router.get("/member/laufzettel/{laufzettel_id}")
async def member_laufzettel_detail(
    request: Request,
    laufzettel_id: int,
    db: Session = Depends(get_laufzettel_db),
    auth_db: Session = Depends(get_auth_db)
):
    """Show member's own laufzettel detail - read only, can add materials"""
    # Check auth manually and redirect to login if not authenticated
    username = request.session.get("user")
    if not username:
        return RedirectResponse("/", status_code=302)
    
    user = auth_db.query(User).filter(User.username == username).first()
    if not user or user.role not in ["admin", "member"]:
        return RedirectResponse("/", status_code=302)
    
    laufzettel = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    
    if not laufzettel:
        raise HTTPException(404, "Laufzettel not found")
    
    # Security check: can only view own laufzettel
    if user.mitglied_id and laufzettel.mitglied_id != user.mitglied_id:
        raise HTTPException(403, "Access denied")
    
    # Get materials for this laufzettel
    materials = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.laufzettel_id == laufzettel_id
    ).all()
    
    return templates.TemplateResponse(
        "member-laufzettel-detail.html",
        {
            "request": request,
            "laufzettel": laufzettel,
            "materials": materials,
            "user": user,
            "read_only": laufzettel.payment_method is not None,  # Can't edit if paid
        },
    )


@router.post("/api/member/laufzettel/{laufzettel_id}/material")
async def member_add_material(
    request: Request,
    laufzettel_id: int,
    variant_id: int,
    menge: float,
    laufzettel_db: Session = Depends(get_laufzettel_db),
    catalog_db: Session = Depends(get_catalog_db),
    user: User = Depends(require_member)
):
    """Member adds material to their own laufzettel"""
    # Check laufzettel exists and belongs to member
    laufzettel = laufzettel_db.query(Laufzettel).filter(
        Laufzettel.id == laufzettel_id
    ).first()
    
    if not laufzettel:
        raise HTTPException(404, "Laufzettel not found")
    
    # Security check
    if user.mitglied_id and laufzettel.mitglied_id != user.mitglied_id:
        raise HTTPException(403, "Access denied")
    
    # Can't add to paid laufzettel
    if laufzettel.payment_method:
        raise HTTPException(400, "Cannot add materials to paid laufzettel")
    
    # Get variant price
    variant = catalog_db.query(MaterialVariante).filter(
        MaterialVariante.id == variant_id
    ).first()
    
    if not variant:
        raise HTTPException(404, "Material variant not found")
    
    # Calculate price
    kategorie = catalog_db.query(MaterialKategorie).filter(
        MaterialKategorie.id == variant.kategorie_id
    ).first()
    
    calculated_price = variant.price * menge

    # Create material entry
    material = LaufzettelMaterial(
        laufzettel_id=laufzettel_id,
        name=variant.name,
        variante_id=variant_id,
        menge=menge,
        unit=kategorie.unit if kategorie else None,
        calculated_price=calculated_price,
    )
    
    laufzettel_db.add(material)
    laufzettel_db.commit()
    
    return {"success": True, "material_id": material.id}


@router.get("/api/member/me")
async def get_current_member_info(
    request: Request,
    user: User = Depends(require_member),
    members_db: Session = Depends(get_members_db)
):
    """Get current member's info"""
    if user.mitglied_id:
        mitglied = members_db.query(Mitglied).filter(
            Mitglied.id == user.mitglied_id
        ).first()
        return {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "mitglied_id": user.mitglied_id,
            "mitglied": mitglied.to_dict() if mitglied else None,
        }
    
    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "mitglied_id": None,
        "mitglied": None,
    }


@router.post("/api/auth/login-rfid")
async def login_via_rfid(
    request: Request,
    auth_db: Session = Depends(get_auth_db),
    members_db: Session = Depends(get_members_db)
):
    """Login via RFID card - creates user if not exists"""
    body = await request.json()
    rfid_uid = body.get("rfid_uid", "").strip().upper()
    from datetime import datetime, timezone

    logger.info("[RFID-LOGIN] Attempt with uid=%r", rfid_uid)

    # Primary lookup: find member directly by nfc_uid
    mitglied = members_db.query(Mitglied).filter(
        Mitglied.nfc_uid == rfid_uid
    ).first()
    logger.info("[RFID-LOGIN] Mitglied by nfc_uid: %s", mitglied.name if mitglied else None)

    # Also check legacy RFIDTag table for admin flag
    tag = members_db.query(RFIDTag).filter(RFIDTag.uid == rfid_uid).first()
    logger.info("[RFID-LOGIN] RFIDTag found: %s", bool(tag))

    if not mitglied and not tag:
        logger.warning("[RFID-LOGIN] uid=%r not found in nfc_uid or rfid_tags", rfid_uid)
        return JSONResponse(
            {"success": False, "error": "Unknown RFID card"},
            status_code=404
        )

    # If tag exists but mitglied not found via nfc_uid, try via RFIDTag.member_id
    if not mitglied and tag:
        mitglied = members_db.query(Mitglied).filter(
            Mitglied.member_id == tag.member_id
        ).first()
        logger.info("[RFID-LOGIN] Mitglied via RFIDTag.member_id=%r: %s", tag.member_id, mitglied.name if mitglied else None)

    if not mitglied:
        logger.warning("[RFID-LOGIN] uid=%r: tag found but no associated Mitglied", rfid_uid)
        return JSONResponse(
            {"success": False, "error": "No member associated with this card"},
            status_code=404
        )

    is_admin_card = bool(tag and tag.is_admin)
    logger.info("[RFID-LOGIN] Mitglied=%r id=%s, is_admin_card=%s", mitglied.name, mitglied.id, is_admin_card)

    # Find or create user for this member
    user = auth_db.query(User).filter(
        User.mitglied_id == mitglied.id
    ).first()

    if not user:
        role = "admin" if is_admin_card else "member"
        user = User(
            username=f"member_{mitglied.id}",
            hashed_password="",  # No password for RFID-only users
            role=role,
            mitglied_id=mitglied.id
        )
        auth_db.add(user)
        auth_db.commit()
        auth_db.refresh(user)

    # Create unified session
    request.session["user"] = user.username
    request.session["mitglied_id"] = user.mitglied_id
    request.session["is_admin_capable"] = user.role == "admin" or is_admin_card
    request.session["admin_verified"] = False  # Always start unverified
    request.session["admin_verified_at"] = None
    request.session["last_activity"] = datetime.now(timezone.utc).isoformat()

    return {
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "mitglied_id": user.mitglied_id,
        },
        "mitglied": mitglied.to_dict(),
        "is_admin_capable": request.session["is_admin_capable"],
        "redirect": "/member"
    }

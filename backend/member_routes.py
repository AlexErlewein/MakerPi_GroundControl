"""Member routes - member-only access to own laufzettel"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.laufzettel.pdf import generate_pdf, pdf_filename

import logging
from datetime import datetime, timezone

from backend.auth.db import get_db as get_auth_db
from backend.auth.models import User
from backend.auth.dependencies import is_member_session_valid
from backend.laufzettel.db import get_db as get_laufzettel_db
from backend.laufzettel.models import Laufzettel, LaufzettelMaterial
from backend.laufzettel.routes import MaterialCreate
from backend.members.db import get_db as get_members_db
from backend.members.models import Mitglied, RFIDTag
from backend.catalog.db import get_db as get_catalog_db
from backend.catalog.models import (
    Location,
    MaterialKategorie,
    MaterialUnterkategorie,
    MaterialVariante,
)
from backend.laufzettel.utils import handle_stale_laufzettel

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")


def require_member(request: Request, db: Session = Depends(get_auth_db)):
    """Check if user is logged in as member or admin"""
    username = request.session.get("user")
    cookie_header = request.headers.get("cookie", "")
    logger.warning(
        "require_member: user=%r session_keys=%r cookie_present=%r ua=%r",
        username,
        list(request.session.keys()),
        bool(cookie_header),
        request.headers.get("user-agent", "")[:80],
    )
    if not username:
        raise HTTPException(401, "Not authenticated")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(401, "User not found")

    if user.role not in ["admin", "member"]:
        raise HTTPException(403, "Access denied")

    # Keep session alive on every API call (same as heartbeat)
    request.session["last_activity"] = datetime.now(timezone.utc).isoformat()

    return user


@router.get("/member")
async def member_dashboard(request: Request, db: Session = Depends(get_auth_db)):
    """Member dashboard - redirects to their open laufzettel"""
    if not is_member_session_valid(request):
        return RedirectResponse("/", status_code=302)
    username = request.session.get("user")
    if not username:
        return RedirectResponse("/", status_code=302)

    user = db.query(User).filter(User.username == username).first()
    if not user or user.role not in ["admin", "member"]:
        return RedirectResponse("/", status_code=302)

    return RedirectResponse("/member/laufzettel", status_code=302)


@router.get("/member/laufzettel")
async def member_laufzettel_open(
    request: Request,
    db: Session = Depends(get_laufzettel_db),
    auth_db: Session = Depends(get_auth_db),
    catalog_db: Session = Depends(get_catalog_db),
):
    """Show member's current open (unpaid) laufzettel"""
    if not is_member_session_valid(request):
        return RedirectResponse("/", status_code=302)
    username = request.session.get("user")
    if not username:
        return RedirectResponse("/", status_code=302)

    user = auth_db.query(User).filter(User.username == username).first()
    if not user or user.role not in ["admin", "member"]:
        return RedirectResponse("/", status_code=302)

    # Handle stale open laufzettel from previous days before showing current one
    if user.mitglied_id:
        handle_stale_laufzettel(user.mitglied_id, db)

    open_lz = None
    materials = []
    if user.mitglied_id:
        # Primary: find open (unpaid) by mitglied_id
        open_lz = (
            db.query(Laufzettel)
            .filter(
                Laufzettel.mitglied_id == user.mitglied_id,
                Laufzettel.payment_method.is_(None),
            )
            .order_by(Laufzettel.created_at.desc())
            .first()
        )

        # Fallback: if not found by mitglied_id, try uid-based lookup
        if not open_lz:
            from backend.members.db import get_db as get_members_db_fn

            members_db = next(get_members_db_fn())
            try:
                from backend.members.models import Mitglied as _Mitglied

                mitglied = (
                    members_db.query(_Mitglied)
                    .filter(_Mitglied.id == user.mitglied_id)
                    .first()
                )
                if mitglied and mitglied.nfc_uid:
                    open_lz = (
                        db.query(Laufzettel)
                        .filter(
                            Laufzettel.uid == mitglied.nfc_uid,
                            Laufzettel.mitglied_id.is_(None),
                            Laufzettel.payment_method.is_(None),
                        )
                        .order_by(Laufzettel.created_at.desc())
                        .first()
                    )
            finally:
                members_db.close()

        if open_lz:
            materials = (
                db.query(LaufzettelMaterial)
                .filter(LaufzettelMaterial.laufzettel_id == open_lz.id)
                .all()
            )

    total = sum(m.calculated_price or 0 for m in materials)
    materials_dicts = [m.to_dict() for m in materials]

    locations = catalog_db.query(Location).order_by(Location.name).all()
    katalog_data = []
    for loc in locations:
        loc_dict = loc.to_dict()
        kategorien = (
            catalog_db.query(MaterialKategorie)
            .filter(MaterialKategorie.location_id == loc.id)
            .order_by(MaterialKategorie.name)
            .all()
        )
        loc_dict["kategorien"] = []
        for kat in kategorien:
            kat_dict = kat.to_dict()
            unterkategorien = (
                catalog_db.query(MaterialUnterkategorie)
                .filter(MaterialUnterkategorie.kategorie_id == kat.id)
                .order_by(MaterialUnterkategorie.name)
                .all()
            )
            kat_dict["unterkategorien"] = []
            for ukat in unterkategorien:
                ukat_dict = ukat.to_dict()
                varianten = (
                    catalog_db.query(MaterialVariante)
                    .filter(MaterialVariante.unterkategorie_id == ukat.id)
                    .order_by(MaterialVariante.id)
                    .all()
                )
                ukat_dict["varianten"] = [v.to_dict() for v in varianten]
                kat_dict["unterkategorien"].append(ukat_dict)
            loc_dict["kategorien"].append(kat_dict)
        katalog_data.append(loc_dict)

    return templates.TemplateResponse(
        "member-laufzettel-open.html",
        {
            "request": request,
            "nav_active": "auftrag",
            "open_lz": open_lz,
            "materials": materials_dicts,
            "total": total,
            "user": user,
            "katalog": katalog_data,
        },
    )


@router.get("/member/laufzettel/historie")
async def member_laufzettel_historie(
    request: Request,
    db: Session = Depends(get_laufzettel_db),
    auth_db: Session = Depends(get_auth_db),
):
    """Show member's paid laufzettel history"""
    if not is_member_session_valid(request):
        return RedirectResponse("/", status_code=302)
    username = request.session.get("user")
    if not username:
        return RedirectResponse("/", status_code=302)

    user = auth_db.query(User).filter(User.username == username).first()
    if not user or user.role not in ["admin", "member"]:
        return RedirectResponse("/", status_code=302)

    history_list = []
    if user.mitglied_id:
        paid = (
            db.query(Laufzettel)
            .filter(
                Laufzettel.mitglied_id == user.mitglied_id,
                Laufzettel.payment_method.isnot(None),
            )
            .order_by(Laufzettel.date.desc())
            .all()
        )

        all_ids = [lz.id for lz in paid]
        totals = {}
        if all_ids:
            mats = (
                db.query(LaufzettelMaterial)
                .filter(LaufzettelMaterial.laufzettel_id.in_(all_ids))
                .all()
            )
            for m in mats:
                totals[m.laufzettel_id] = totals.get(m.laufzettel_id, 0) + (
                    m.calculated_price or 0
                )

        history_list = [
            {"laufzettel": lz, "total": totals.get(lz.id, 0.0)} for lz in paid
        ]

    return templates.TemplateResponse(
        "member-laufzettel-historie.html",
        {
            "request": request,
            "nav_active": "historie",
            "history_list": history_list,
            "user": user,
        },
    )


@router.get("/api/member/laufzettel/{laufzettel_id}/pdf")
async def member_download_pdf(
    request: Request,
    laufzettel_id: int,
    db: Session = Depends(get_laufzettel_db),
    auth_db: Session = Depends(get_auth_db),
):
    """Generate and return PDF for member's own laufzettel."""
    if not is_member_session_valid(request):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = (
        auth_db.query(User).filter(User.username == request.session.get("user")).first()
    )
    if not user or user.role not in ["admin", "member"]:
        raise HTTPException(status_code=401, detail="Not authenticated")

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")

    # Security check: can only download own laufzettel
    if user.mitglied_id and lz.mitglied_id != user.mitglied_id:
        raise HTTPException(status_code=403, detail="Access denied")

    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == laufzettel_id)
        .all()
    )
    pdf_bytes = generate_pdf(lz, materials)
    filename = pdf_filename(lz)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/member/laufzettel/{laufzettel_id}")
async def member_laufzettel_detail(
    request: Request,
    laufzettel_id: int,
    db: Session = Depends(get_laufzettel_db),
    auth_db: Session = Depends(get_auth_db),
    catalog_db: Session = Depends(get_catalog_db),
):
    """Show member's laufzettel detail - read only (history view)"""
    if not is_member_session_valid(request):
        return RedirectResponse("/", status_code=302)
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

    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == laufzettel_id)
        .all()
    )

    total = sum(m.calculated_price or 0 for m in materials)
    materials_dicts = [m.to_dict() for m in materials]

    # Load catalog tree for location grouping in frontend
    locations = catalog_db.query(Location).order_by(Location.name).all()
    katalog_data = []
    for loc in locations:
        loc_dict = loc.to_dict()
        kategorien = (
            catalog_db.query(MaterialKategorie)
            .filter(MaterialKategorie.location_id == loc.id)
            .order_by(MaterialKategorie.name)
            .all()
        )
        loc_dict["kategorien"] = []
        for kat in kategorien:
            kat_dict = kat.to_dict()
            varianten = (
                catalog_db.query(MaterialVariante)
                .filter(MaterialVariante.kategorie_id == kat.id)
                .order_by(MaterialVariante.name)
                .all()
            )
            kat_dict["varianten"] = [v.to_dict() for v in varianten]
            loc_dict["kategorien"].append(kat_dict)
        katalog_data.append(loc_dict)

    return templates.TemplateResponse(
        "member-laufzettel-detail.html",
        {
            "request": request,
            "nav_active": "auftrag",
            "laufzettel": laufzettel,
            "materials": materials_dicts,
            "total": total,
            "user": user,
            "read_only": laufzettel.payment_method is not None,
            "back_url": "/member/laufzettel/historie",
            "katalog": katalog_data,
        },
    )


@router.get("/member/konto")
async def member_konto(
    request: Request,
    auth_db: Session = Depends(get_auth_db),
    members_db: Session = Depends(get_members_db),
):
    """Show member account info"""
    if not is_member_session_valid(request):
        return RedirectResponse("/", status_code=302)
    username = request.session.get("user")
    if not username:
        return RedirectResponse("/", status_code=302)

    user = auth_db.query(User).filter(User.username == username).first()
    if not user or user.role not in ["admin", "member"]:
        return RedirectResponse("/", status_code=302)

    mitglied = None
    if user.mitglied_id:
        mitglied = (
            members_db.query(Mitglied).filter(Mitglied.id == user.mitglied_id).first()
        )

    return templates.TemplateResponse(
        "member-konto.html",
        {
            "request": request,
            "nav_active": "konto",
            "user": user,
            "mitglied": mitglied,
        },
    )


@router.post("/api/member/laufzettel/{laufzettel_id}/material")
async def member_add_material(
    laufzettel_id: int,
    mat: MaterialCreate,
    laufzettel_db: Session = Depends(get_laufzettel_db),
    user: User = Depends(require_member),
):
    """Member adds material to their own laufzettel"""
    laufzettel = (
        laufzettel_db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    )

    if not laufzettel:
        raise HTTPException(404, "Laufzettel not found")

    if user.mitglied_id and laufzettel.mitglied_id != user.mitglied_id:
        raise HTTPException(403, "Access denied")

    if laufzettel.payment_method:
        raise HTTPException(400, "Cannot add materials to paid laufzettel")

    new_mat = LaufzettelMaterial(
        laufzettel_id=laufzettel_id,
        name=mat.name,
        menge=mat.menge,
        variante_id=mat.variante_id,
        unit=mat.unit,
        laenge_cm=mat.laenge_cm,
        breite_cm=mat.breite_cm,
        hoehe_cm=mat.hoehe_cm,
        calculated_price=mat.calculated_price,
        tax_rate=mat.tax_rate if mat.tax_rate is not None else None,
    )

    laufzettel_db.add(new_mat)
    laufzettel_db.commit()
    laufzettel_db.refresh(new_mat)

    return new_mat.to_dict()


@router.get("/api/member/me")
async def get_current_member_info(
    request: Request,
    user: User = Depends(require_member),
    members_db: Session = Depends(get_members_db),
):
    """Get current member's info"""
    if user.mitglied_id:
        mitglied = (
            members_db.query(Mitglied).filter(Mitglied.id == user.mitglied_id).first()
        )
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
    members_db: Session = Depends(get_members_db),
):
    """Login via RFID card - creates user if not exists"""
    body = await request.json()
    rfid_uid = body.get("rfid_uid", "").strip().upper()
    from datetime import datetime, timezone

    logger.info(
        "[RFID-LOGIN] Attempt with uid=%r, cookie=%r",
        rfid_uid,
        request.headers.get("cookie", "")[:100],
    )

    # Primary lookup: find member directly by nfc_uid
    mitglied = members_db.query(Mitglied).filter(Mitglied.nfc_uid == rfid_uid).first()
    logger.info(
        "[RFID-LOGIN] Mitglied by nfc_uid: %s", mitglied.name if mitglied else None
    )

    # Also check legacy RFIDTag table for admin flag
    tag = members_db.query(RFIDTag).filter(RFIDTag.uid == rfid_uid).first()
    logger.info("[RFID-LOGIN] RFIDTag found: %s", bool(tag))

    if not mitglied and not tag:
        logger.warning(
            "[RFID-LOGIN] uid=%r not found in nfc_uid or rfid_tags", rfid_uid
        )
        return JSONResponse(
            {"success": False, "error": "Unknown RFID card"}, status_code=404
        )

    # If tag exists but mitglied not found via nfc_uid, try via RFIDTag.member_id
    if not mitglied and tag:
        mitglied = (
            members_db.query(Mitglied)
            .filter(Mitglied.member_id == tag.member_id)
            .first()
        )
        logger.info(
            "[RFID-LOGIN] Mitglied via RFIDTag.member_id=%r: %s",
            tag.member_id,
            mitglied.name if mitglied else None,
        )

    if not mitglied:
        logger.warning(
            "[RFID-LOGIN] uid=%r: tag found but no associated Mitglied", rfid_uid
        )
        return JSONResponse(
            {"success": False, "error": "No member associated with this card"},
            status_code=404,
        )

    is_admin_card = bool(tag and tag.is_admin)
    logger.info(
        "[RFID-LOGIN] Mitglied=%r id=%s, is_admin_card=%s",
        mitglied.name,
        mitglied.id,
        is_admin_card,
    )

    # Find or create user for this member
    user = auth_db.query(User).filter(User.mitglied_id == mitglied.id).first()

    if not user:
        role = "admin" if is_admin_card else "member"
        # Use member's real name as username; fall back to member_ID if already taken
        desired_username = (
            mitglied.name.strip() if mitglied.name else f"member_{mitglied.id}"
        )
        existing = auth_db.query(User).filter(User.username == desired_username).first()
        username = desired_username if not existing else f"member_{mitglied.id}"
        user = User(
            username=username,
            hashed_password="",
            role=role,
            mitglied_id=mitglied.id,
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

    logger.info(
        "[RFID-LOGIN] Session created for user=%s mitglied_id=%s is_admin=%s",
        user.username,
        user.mitglied_id,
        request.session["is_admin_capable"],
    )

    # Handle stale open laufzettel from previous days
    stale_result = {"action": "none"}
    if user.mitglied_id:
        from backend.laufzettel.db import get_db as get_lz_db_fn

        lz_db = next(get_lz_db_fn())
        try:
            stale_result = handle_stale_laufzettel(user.mitglied_id, lz_db)
        except Exception:
            logger.exception(
                "[RFID-LOGIN] handle_stale_laufzettel failed for mitglied_id=%s",
                user.mitglied_id,
            )
        finally:
            lz_db.close()

    result = {
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "mitglied_id": user.mitglied_id,
        },
        "mitglied": mitglied.to_dict(),
        "is_admin_capable": request.session["is_admin_capable"],
        "redirect": "/member",
        "stale_laufzettel": stale_result.get("action"),
    }
    logger.info(
        "[RFID-LOGIN] Returning success for user=%s redirect=%s",
        user.username,
        result["redirect"],
    )
    return result


# ── Kasse (Payment Checkout) ────────────────────────────────────────────────


@router.get("/kasse")
async def kasse_page(request: Request):
    """Standalone payment checkout page — no auth required."""
    return templates.TemplateResponse("kasse.html", {"request": request})


@router.get("/api/kasse/lookup")
async def kasse_lookup(
    uid: str,
    laufzettel_db: Session = Depends(get_laufzettel_db),
    members_db: Session = Depends(get_members_db),
):
    """Look up a member's open laufzettel by NFC UID."""
    uid = uid.strip().upper()

    mitglied = members_db.query(Mitglied).filter(Mitglied.nfc_uid == uid).first()
    if not mitglied:
        return JSONResponse({"error": "Unbekannte Karte"}, status_code=404)

    # Find open (unpaid) laufzettel for this member
    open_lz = (
        laufzettel_db.query(Laufzettel)
        .filter(
            Laufzettel.mitglied_id == mitglied.id,
            Laufzettel.payment_method.is_(None),
        )
        .order_by(Laufzettel.created_at.desc())
        .first()
    )

    # Fallback: try uid-based lookup
    if not open_lz:
        open_lz = (
            laufzettel_db.query(Laufzettel)
            .filter(
                Laufzettel.uid == uid,
                Laufzettel.mitglied_id.is_(None),
                Laufzettel.payment_method.is_(None),
            )
            .order_by(Laufzettel.created_at.desc())
            .first()
        )

    if not open_lz:
        return JSONResponse(
            {"error": "Kein offener Laufzettel gefunden", "mitglied": mitglied.name},
            status_code=404,
        )

    # Get materials total
    materials = (
        laufzettel_db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == open_lz.id)
        .all()
    )
    total = sum(m.calculated_price or 0 for m in materials)

    return {
        "mitglied": {
            "id": mitglied.id,
            "name": mitglied.name,
            "member_id": mitglied.member_id,
        },
        "laufzettel": {
            "id": open_lz.id,
            "date": str(open_lz.date) if open_lz.date else None,
            "material_count": len(materials),
            "total": round(total, 2),
        },
    }


@router.post("/api/kasse/verify-admin-card")
async def kasse_verify_admin_card(
    request: Request,
    members_db: Session = Depends(get_members_db),
    auth_db: Session = Depends(get_auth_db),
):
    """Verify an admin NFC card and create an admin session for payment."""
    from datetime import datetime, timezone

    body = await request.json()
    rfid_uid = body.get("rfid_uid", "").strip().upper()

    if not rfid_uid:
        return JSONResponse({"success": False, "error": "Keine UID"}, status_code=400)

    # Check RFIDTag for admin flag
    tag = (
        members_db.query(RFIDTag)
        .filter(RFIDTag.uid == rfid_uid, RFIDTag.active == 1)
        .first()
    )

    is_admin_card = bool(tag and tag.is_admin)

    if not is_admin_card:
        # Also check if the associated user is an admin
        mitglied = (
            members_db.query(Mitglied).filter(Mitglied.nfc_uid == rfid_uid).first()
        )
        if mitglied:
            user = auth_db.query(User).filter(User.mitglied_id == mitglied.id).first()
            if user and user.role == "admin":
                is_admin_card = True

    if not is_admin_card:
        return JSONResponse(
            {"success": False, "error": "Keine Admin-Berechtigung"},
            status_code=403,
        )

    # Create admin session
    # Find or create user for admin card holder
    mitglied = members_db.query(Mitglied).filter(Mitglied.nfc_uid == rfid_uid).first()
    if not mitglied and tag and tag.member_id:
        mitglied = (
            members_db.query(Mitglied)
            .filter(Mitglied.member_id == tag.member_id)
            .first()
        )

    user = None
    if mitglied:
        user = auth_db.query(User).filter(User.mitglied_id == mitglied.id).first()

    if user:
        request.session["user"] = user.username
        request.session["mitglied_id"] = user.mitglied_id
    else:
        request.session["user"] = tag.owner_name or "admin"
        request.session["mitglied_id"] = None

    request.session["is_admin_capable"] = True
    request.session["admin_verified"] = True
    request.session["admin_verified_at"] = datetime.now(timezone.utc).isoformat()
    request.session["last_activity"] = datetime.now(timezone.utc).isoformat()

    return {"success": True}

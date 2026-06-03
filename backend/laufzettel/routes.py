"""Laufzettel routes - API and pages for work orders"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json

from backend.config import (
    PUBLIC_BASE_URL,
    SUMUP_API_KEY,
    SUMUP_MERCHANT_CODE,
    SUMUP_READER_ID,
    SUMUP_AFFILIATE_KEY,
    SUMUP_MOCK,
    WERO_ENABLED,
    WERO_MOCK,
)
from .db import get_db, init_db
from .models import Laufzettel, LaufzettelGutschein, LaufzettelMaterial
from .pdf import drive_folder_names, generate_pdf, pdf_filename
from .utils import handle_stale_laufzettel

# Push notification support (import at module level, calls wrapped in try/except)
try:
    from backend.push.routes import send_push_notification
except Exception:
    send_push_notification = None  # Optional module
    pass

# Email support (import at module level, calls wrapped in try/except)
try:
    from backend.email_utils import send_email as _send_email
    from backend.email_templates import easyverein_signup_html, laufzettel_receipt_html
except Exception:
    _send_email = None
    laufzettel_receipt_html = None
    easyverein_signup_html = None

logger = logging.getLogger(__name__)

router = APIRouter()


def _schedule_pdf_upload(lz: Laufzettel, materials: list) -> None:
    """Fire-and-forget: generate PDF and upload to Google Drive in the background.

    A Drive failure must never affect the payment response.
    """
    from backend.gdrive import upload_pdf

    try:
        pdf_bytes = generate_pdf(lz, materials)
        filename = pdf_filename(lz)
        year, month = drive_folder_names(lz)
        asyncio.get_event_loop().run_in_executor(
            None, upload_pdf, pdf_bytes, filename, year, month
        )
    except Exception:
        logger.exception("PDF generation failed for Laufzettel #%s", lz.id)


def _get_laufzettel_email(lz: "Laufzettel") -> str | None:
    """Return the best email address for a Laufzettel's owner, or None."""
    if lz.guest_email:
        return lz.guest_email
    try:
        from backend.members.db import SessionLocal as MembersSession
        from backend.members.models import Mitglied, RFIDTag

        members_db = MembersSession()
        try:
            if lz.mitglied_id:
                m = (
                    members_db.query(Mitglied)
                    .filter(Mitglied.id == lz.mitglied_id)
                    .first()
                )
                if m and m.email:
                    return m.email
            if lz.uid and not lz.uid.startswith("GUEST-"):
                m = (
                    members_db.query(Mitglied)
                    .filter(Mitglied.nfc_uid == lz.uid)
                    .first()
                )
                if m and m.email:
                    return m.email
                tag = (
                    members_db.query(RFIDTag)
                    .filter(RFIDTag.uid == lz.uid, RFIDTag.active == 1)
                    .first()
                )
                if tag and tag.owner_email:
                    return tag.owner_email
        finally:
            members_db.close()
    except Exception:
        pass
    return None


def _schedule_receipt_email(
    lz: "Laufzettel", materials: list, request: Request = None
) -> None:
    """Fire-and-forget: email a payment receipt to the Laufzettel owner.

    An email failure must never affect the payment response.
    """
    if not _send_email or not laufzettel_receipt_html:
        return
    try:
        recipient = _get_laufzettel_email(lz)
        if not recipient:
            return

        # Construct view URL for the Laufzettel
        if PUBLIC_BASE_URL:
            base_url = PUBLIC_BASE_URL
        elif request:
            base_url = f"{request.url.scheme}://{request.url.netloc}"
        else:
            base_url = "https://h3cke.de"
        view_url = f"{base_url}/laufzettel/view/{lz.id}"

        html = laufzettel_receipt_html(lz, materials, view_url)
        asyncio.create_task(
            _send_email(
                to=recipient,
                subject=f"Laufzettel #{lz.id} – Quittung",
                html_body=html,
            )
        )
    except Exception:
        logger.exception("Failed to schedule receipt email for Laufzettel #%s", lz.id)


class LaufzettelCreate(BaseModel):
    uid: str
    date: Optional[str] = None  # ISO date string
    owner_name: Optional[str] = None
    member_id: Optional[str] = None
    start: Optional[str] = None  # ISO datetime


class LaufzettelUpdate(BaseModel):
    owner_name: Optional[str] = None
    member_id: Optional[str] = None
    start: Optional[str] = None


class MaterialCreate(BaseModel):
    name: str
    menge: Optional[float] = None
    variante_id: Optional[int] = None
    unit: Optional[str] = None
    laenge_cm: Optional[float] = None
    breite_cm: Optional[float] = None
    hoehe_cm: Optional[float] = None
    calculated_price: Optional[float] = None
    tax_rate: Optional[float] = None
    is_spende: Optional[bool] = None


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    menge: Optional[float] = None
    variante_id: Optional[int] = None
    unit: Optional[str] = None
    laenge_cm: Optional[float] = None
    breite_cm: Optional[float] = None
    hoehe_cm: Optional[float] = None
    calculated_price: Optional[float] = None
    tax_rate: Optional[float] = None
    is_spende: Optional[bool] = None


@router.on_event("startup")
async def startup():
    init_db()


# ── Pages ───────────────────────────────────────────────────────────────────


@router.get("/laufzettel", response_class=HTMLResponse)
async def laufzettel_page(request: Request):
    """Render Laufzettel list page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth

    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "laufzettel.html",
        {
            "request": request,
            "nav_active": "laufzettel",
            "current_user": request.session.get("user"),
        },
    )


@router.get("/laufzettel/{laufzettel_id}", response_class=HTMLResponse)
async def laufzettel_detail_page(
    request: Request, laufzettel_id: int, db: Session = Depends(get_db)
):
    """Render Laufzettel detail/edit page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth

    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    return templates.TemplateResponse(
        "laufzettel-detail.html",
        {
            "request": request,
            "laufzettel_id": laufzettel_id,
            "nav_active": "laufzettel",
            "current_user": request.session.get("user"),
        },
    )


# ── API ──────────────────────────────────────────────────────────────────────


@router.post("/api/laufzettel")
async def create_laufzettel(data: LaufzettelCreate, db: Session = Depends(get_db)):
    """Manually create a new Laufzettel entry"""
    from datetime import datetime, date as dt_date

    uid = data.uid.upper()
    if data.date:
        try:
            entry_date = dt_date.fromisoformat(data.date)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid date format, use YYYY-MM-DD"},
            )
    else:
        entry_date = dt_date.today()

    existing_open = (
        db.query(Laufzettel)
        .filter(
            Laufzettel.uid == uid,
            Laufzettel.date == entry_date,
            Laufzettel.payment_method.is_(None),
        )
        .first()
    )
    if existing_open:
        return JSONResponse(
            status_code=400,
            content={
                "detail": f"An open (unpaid) Laufzettel for {uid} on {entry_date} already exists (id={existing_open.id})"
            },
        )

    start_dt = None
    if data.start:
        try:
            start_dt = datetime.fromisoformat(data.start)
        except ValueError:
            return JSONResponse(
                status_code=400, content={"detail": "Invalid start datetime format"}
            )

    # Auto-resolve owner_name and mitglied_id from Mitglied.nfc_uid if not provided
    resolved_mitglied_id = data.member_id  # keep string member_id for legacy
    resolved_mitglied_db_id = None
    resolved_owner_name = data.owner_name
    try:
        from backend.members.db import SessionLocal as MembersSession
        from backend.members.models import Mitglied, RFIDTag

        members_db = MembersSession()
        try:
            mitglied = (
                members_db.query(Mitglied).filter(Mitglied.nfc_uid == uid).first()
            )
            if mitglied:
                resolved_mitglied_db_id = mitglied.id
                if not resolved_owner_name:
                    resolved_owner_name = mitglied.name
                if not resolved_mitglied_id:
                    resolved_mitglied_id = mitglied.member_id
            else:
                tag = (
                    members_db.query(RFIDTag)
                    .filter(RFIDTag.uid == uid, RFIDTag.active == 1)
                    .first()
                )
                if tag:
                    if not resolved_owner_name:
                        resolved_owner_name = tag.owner_name
                    if not resolved_mitglied_id:
                        resolved_mitglied_id = tag.member_id
                    if tag.member_id:
                        m = (
                            members_db.query(Mitglied)
                            .filter(Mitglied.member_id == tag.member_id)
                            .first()
                        )
                        if m:
                            resolved_mitglied_db_id = m.id
        finally:
            members_db.close()
    except Exception:
        pass

    # Handle stale laufzettel from previous days before creating a new one
    if resolved_mitglied_db_id:
        try:
            handle_stale_laufzettel(resolved_mitglied_db_id, db)
        except Exception:
            logger.exception(
                "handle_stale_laufzettel failed for mitglied_id=%s",
                resolved_mitglied_db_id,
            )

    # Re-check for an existing open laufzettel for today (may have been created by carry-over)
    existing_open = (
        (
            db.query(Laufzettel)
            .filter(
                Laufzettel.mitglied_id == resolved_mitglied_db_id,
                Laufzettel.date == entry_date,
                Laufzettel.payment_method.is_(None),
            )
            .first()
        )
        if resolved_mitglied_db_id
        else existing_open
    )
    if existing_open:
        materials = (
            db.query(LaufzettelMaterial)
            .filter(LaufzettelMaterial.laufzettel_id == existing_open.id)
            .all()
        )
        d = existing_open.to_dict()
        d["material"] = [m.to_dict() for m in materials]
        return d

    lz = Laufzettel(
        uid=uid,
        date=entry_date,
        start=start_dt,
        owner_name=resolved_owner_name,
        member_id=resolved_mitglied_id,
        mitglied_id=resolved_mitglied_db_id,
        nodes=json.dumps([]),
    )
    db.add(lz)
    db.commit()
    db.refresh(lz)
    d = lz.to_dict()
    d["material"] = []
    return d


@router.get("/api/laufzettel")
async def get_laufzettel(
    uid: Optional[str] = None, date: Optional[str] = None, db: Session = Depends(get_db)
):
    """List all Laufzettel entries, optionally filtered"""
    from datetime import date as dt_date

    query = db.query(Laufzettel)
    if uid:
        query = query.filter(Laufzettel.uid == uid.upper())
    if date:
        try:
            parsed_date = dt_date.fromisoformat(date)
            query = query.filter(Laufzettel.date == parsed_date)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid date format, use YYYY-MM-DD"},
            )
    entries = query.order_by(Laufzettel.date.desc(), Laufzettel.start.desc()).all()
    result = []
    for lz in entries:
        d = lz.to_dict()
        materials = (
            db.query(LaufzettelMaterial)
            .filter(LaufzettelMaterial.laufzettel_id == lz.id)
            .all()
        )
        d["material"] = [m.to_dict() for m in materials]
        result.append(d)
    return result


@router.get("/api/laufzettel/{laufzettel_id}")
async def get_laufzettel_detail(
    laufzettel_id: int, request: Request, db: Session = Depends(get_db)
):
    """Get a single Laufzettel with its material entries"""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    # Allow guest access via cookie
    if not _check_guest_access(request, lz):
        from backend.auth.dependencies import check_auth

        if not check_auth(request):
            raise HTTPException(status_code=401, detail="Authentication required")
    d = lz.to_dict()
    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == lz.id)
        .all()
    )
    d["material"] = [m.to_dict() for m in materials]
    _enrich_with_gutschein(d, db, materials)
    return d


@router.get("/api/tags/{uid}/laufzettel")
async def get_laufzettel_for_tag(uid: str, db: Session = Depends(get_db)):
    """Get all Laufzettel entries for a specific tag"""
    entries = (
        db.query(Laufzettel)
        .filter(Laufzettel.uid == uid.upper())
        .order_by(Laufzettel.date.desc())
        .all()
    )
    result = []
    for lz in entries:
        d = lz.to_dict()
        materials = (
            db.query(LaufzettelMaterial)
            .filter(LaufzettelMaterial.laufzettel_id == lz.id)
            .all()
        )
        d["material"] = [m.to_dict() for m in materials]
        result.append(d)
    return result


@router.put("/api/laufzettel/{laufzettel_id}")
async def update_laufzettel(
    laufzettel_id: int, data: LaufzettelUpdate, db: Session = Depends(get_db)
):
    """Update editable fields of a Laufzettel"""
    from datetime import datetime

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(
            status_code=409, detail="Laufzettel is already paid and locked"
        )
    if data.owner_name is not None:
        lz.owner_name = data.owner_name
    if data.member_id is not None:
        lz.member_id = data.member_id
    if data.start is not None:
        try:
            lz.start = datetime.fromisoformat(data.start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start datetime format")
    db.commit()
    db.refresh(lz)
    d = lz.to_dict()
    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == lz.id)
        .all()
    )
    d["material"] = [m.to_dict() for m in materials]
    return d


@router.post("/api/laufzettel/{laufzettel_id}/material")
async def add_material(
    laufzettel_id: int,
    mat: MaterialCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Add a material entry to a Laufzettel"""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(
            status_code=409, detail="Laufzettel is already paid and locked"
        )
    # Allow guest access via cookie
    if not _check_guest_access(request, lz):
        from backend.auth.dependencies import check_auth

        if not check_auth(request):
            raise HTTPException(status_code=401, detail="Authentication required")
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
        is_spende=bool(mat.is_spende) if mat.is_spende is not None else False,
    )
    db.add(new_mat)
    db.commit()
    db.refresh(new_mat)
    return new_mat.to_dict()


@router.put("/api/laufzettel/{laufzettel_id}/material/{material_id}")
async def update_material(
    laufzettel_id: int,
    material_id: int,
    mat: MaterialUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update a material entry"""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if lz and lz.payment_method:
        raise HTTPException(
            status_code=409, detail="Laufzettel is already paid and locked"
        )
    # Allow guest access via cookie
    if lz and not _check_guest_access(request, lz):
        from backend.auth.dependencies import check_auth

        if not check_auth(request):
            raise HTTPException(status_code=401, detail="Authentication required")
    existing = (
        db.query(LaufzettelMaterial)
        .filter(
            LaufzettelMaterial.id == material_id,
            LaufzettelMaterial.laufzettel_id == laufzettel_id,
        )
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Material entry not found")
    if mat.name is not None:
        existing.name = mat.name
    if mat.menge is not None:
        existing.menge = mat.menge
    if mat.variante_id is not None:
        existing.variante_id = mat.variante_id
    if mat.unit is not None:
        existing.unit = mat.unit
    if mat.laenge_cm is not None:
        existing.laenge_cm = mat.laenge_cm
    if mat.breite_cm is not None:
        existing.breite_cm = mat.breite_cm
    if mat.hoehe_cm is not None:
        existing.hoehe_cm = mat.hoehe_cm
    if mat.calculated_price is not None:
        existing.calculated_price = mat.calculated_price
    if mat.tax_rate is not None:
        existing.tax_rate = mat.tax_rate
    if mat.is_spende is not None:
        existing.is_spende = mat.is_spende
    db.commit()
    db.refresh(existing)
    return existing.to_dict()


@router.delete("/api/laufzettel/{laufzettel_id}")
async def delete_laufzettel(
    laufzettel_id: int, request: Request, db: Session = Depends(get_db)
):
    """Delete a Laufzettel and all its material entries"""
    from backend.auth.dependencies import is_admin_verified

    if not is_admin_verified(request):
        raise HTTPException(status_code=403, detail="Admin verification required")
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.laufzettel_id == laufzettel_id
    ).delete()
    db.delete(lz)
    db.commit()
    return {"deleted": laufzettel_id}


@router.delete("/api/laufzettel/{laufzettel_id}/material/{material_id}")
async def delete_material(
    laufzettel_id: int,
    material_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a material entry"""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if lz and lz.payment_method:
        raise HTTPException(
            status_code=409, detail="Laufzettel is already paid and locked"
        )
    # Allow guest access via cookie
    if lz and not _check_guest_access(request, lz):
        from backend.auth.dependencies import check_auth

        if not check_auth(request):
            raise HTTPException(status_code=401, detail="Authentication required")
    mat = (
        db.query(LaufzettelMaterial)
        .filter(
            LaufzettelMaterial.id == material_id,
            LaufzettelMaterial.laufzettel_id == laufzettel_id,
        )
        .first()
    )
    if not mat:
        raise HTTPException(status_code=404, detail="Material entry not found")
    db.delete(mat)
    db.commit()
    return {"success": True}


# ── PDF download ─────────────────────────────────────────────────────────────


@router.get("/api/laufzettel/{laufzettel_id}/pdf")
async def download_pdf(laufzettel_id: int, db: Session = Depends(get_db)):
    """Generate and return a PDF receipt for the given Laufzettel."""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
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


# ── Payment API ───────────────────────────────────────────────────────────────


@router.get("/api/payment/config")
async def get_payment_config():
    """Return payment configuration for frontend"""
    sumup_configured = bool(SUMUP_API_KEY and SUMUP_MERCHANT_CODE)
    has_reader = bool(SUMUP_READER_ID)
    has_affiliate = bool(SUMUP_AFFILIATE_KEY)
    # payment_mode: 'solo' = Cloud API, 'payment_switch' = URL scheme handoff, 'mock', or None
    if SUMUP_MOCK:
        payment_mode = "mock"
    elif sumup_configured and has_reader:
        payment_mode = "solo"
    elif sumup_configured and has_affiliate:
        payment_mode = "payment_switch"
    else:
        payment_mode = None
    return {
        "sumup_configured": sumup_configured,
        "sumup_mock": SUMUP_MOCK,
        "reader_id": SUMUP_READER_ID if sumup_configured else None,
        "payment_mode": payment_mode,
        "checkout_link_available": sumup_configured and not SUMUP_MOCK,
        "wero_configured": WERO_ENABLED,
        "wero_mock": WERO_MOCK,
    }


class BarPayRequest(BaseModel):
    notes: str = ""


@router.post("/api/laufzettel/{laufzettel_id}/pay/bar")
async def pay_bar(
    laufzettel_id: int,
    request: Request,
    body: BarPayRequest = BarPayRequest(),
    db: Session = Depends(get_db),
):
    """Mark Laufzettel as paid with cash"""
    from datetime import datetime, timezone

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(status_code=409, detail="Already paid")
    lz.payment_method = "bar"
    lz.paid_at = datetime.now(timezone.utc)
    if body.notes:
        lz.payment_notes = body.notes.strip()
    db.commit()
    db.refresh(lz)
    d = lz.to_dict()
    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == lz.id)
        .all()
    )
    d["material"] = [m.to_dict() for m in materials]
    _schedule_pdf_upload(lz, materials)
    _schedule_receipt_email(lz, materials, request)
    from backend.buchhaltung.accounting import record_laufzettel_payment

    record_laufzettel_payment(lz, materials)
    # Push notification (non-critical)
    try:
        if send_push_notification:
            send_push_notification(
                title="Zahlung eingegangen",
                body=f"Laufzettel #{laufzettel_id} — Barzahlung erfasst",
                tag=f"payment-{laufzettel_id}",
                url=f"/laufzettel/{laufzettel_id}",
            )
    except Exception:
        pass
    return d


# In-memory store for pending card payments (transaction_id -> {created_at, status})
_pending_payments: dict = {}


@router.post("/api/laufzettel/{laufzettel_id}/pay/karte")
async def pay_karte(laufzettel_id: int, db: Session = Depends(get_db)):
    """Initiate card payment - returns transaction ID for polling"""
    from datetime import datetime, timezone, timedelta
    import uuid

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(status_code=409, detail="Already paid")

    # Generate transaction ID
    txn_id = str(uuid.uuid4())

    if SUMUP_MOCK:
        # Mock mode: return transaction ID for immediate confirmation
        return {
            "mock": True,
            "client_transaction_id": txn_id,
            "status": "PENDING",
        }

    # Calculate remaining amount (material total minus any applied gift card credits)
    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == laufzettel_id)
        .all()
    )
    mat_total = sum(
        m.calculated_price for m in materials if m.calculated_price is not None
    )
    _, _credited = _calc_gutschein_totals(db, laufzettel_id)
    total = max(0.0, mat_total - _credited)
    amount_str = f"{total:.2f}"

    if SUMUP_READER_ID and SUMUP_API_KEY and SUMUP_MERCHANT_CODE:
        # Solo Cloud API: initiate checkout on terminal
        import httpx

        lz_desc = f"Laufzettel #{laufzettel_id}"
        if lz.owner_name:
            lz_desc += f" – {lz.owner_name}"
        payload = {
            "total_amount": {
                "currency": "EUR",
                "minor_unit": 2,
                "value": int(round(total * 100)),
            },
            "description": lz_desc,
            "affiliate": {
                "app_id": "MakerPi.GroundControl",
                "foreign_transaction_id": txn_id,
                "key": SUMUP_AFFILIATE_KEY,
            }
            if SUMUP_AFFILIATE_KEY
            else None,
        }
        if payload["affiliate"] is None:
            del payload["affiliate"]
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"https://api.sumup.com/v0.1/merchants/{SUMUP_MERCHANT_CODE}/readers/{SUMUP_READER_ID}/checkout",
                headers={"Authorization": f"Bearer {SUMUP_API_KEY}"},
                json=payload,
                timeout=15,
            )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"SumUp API error: {r.text}")
        _pending_payments[txn_id] = {
            "laufzettel_id": laufzettel_id,
            "created_at": datetime.now(timezone.utc),
            "status": "PENDING",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=2),
            "mode": "solo",
        }
        return {
            "mock": False,
            "mode": "solo",
            "client_transaction_id": txn_id,
            "status": "PENDING",
        }

    elif SUMUP_AFFILIATE_KEY:
        # Payment Switch: generate URL scheme for SumUp app handoff
        from urllib.parse import urlencode

        lz_title = f"Laufzettel #{laufzettel_id}"
        if lz.owner_name:
            lz_title += f" – {lz.owner_name}"
        params = {
            "affiliate-key": SUMUP_AFFILIATE_KEY,
            "amount": amount_str,
            "currency": "EUR",
            "foreign-tx-id": txn_id,
            "title": lz_title,
        }
        payment_url = "sumupmerchant://pay/1.0?" + urlencode(params)
        _pending_payments[txn_id] = {
            "laufzettel_id": laufzettel_id,
            "created_at": datetime.now(timezone.utc),
            "status": "PENDING",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "mode": "payment_switch",
            "foreign_tx_id": txn_id,
        }
        return {
            "mock": False,
            "mode": "payment_switch",
            "client_transaction_id": txn_id,
            "payment_url": payment_url,
            "amount": amount_str,
            "status": "PENDING",
        }

    raise HTTPException(
        status_code=503, detail="Keine SumUp-Zahlungsmethode konfiguriert"
    )


@router.get("/api/laufzettel/{laufzettel_id}/pay/karte/status")
async def get_karte_status(
    laufzettel_id: int,
    client_transaction_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Check status of card payment"""
    from datetime import datetime, timezone

    # Check if already paid directly
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if lz and lz.payment_method == "karte":
        d = lz.to_dict()
        materials = (
            db.query(LaufzettelMaterial)
            .filter(LaufzettelMaterial.laufzettel_id == lz.id)
            .all()
        )
        d["material"] = [m.to_dict() for m in materials]
        return {"status": "SUCCESSFUL", "laufzettel": d}

    # Check pending payments
    pending = _pending_payments.get(client_transaction_id)
    if not pending:
        return {"status": "NOT_FOUND"}

    # Check timeout (1 minute)
    if datetime.now(timezone.utc) > pending["expires_at"]:
        # Clean up expired
        del _pending_payments[client_transaction_id]
        return {"status": "TIMEOUT"}

    # For payment_switch, poll recent SumUp transactions and match by product_summary
    # (SumUp does not expose foreign-tx-id from URL scheme as a filterable field)
    if pending["mode"] == "payment_switch" and SUMUP_API_KEY:
        import httpx

        lz_summary_prefix = f"Laufzettel #{laufzettel_id}"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://api.sumup.com/v0.1/me/transactions/history",
                    headers={"Authorization": f"Bearer {SUMUP_API_KEY}"},
                    params={"limit": 10, "order": "descending"},
                    timeout=10,
                )
            if r.status_code == 200:
                for item in r.json().get("items", []):
                    summary = item.get("product_summary", "")
                    if item.get("status") == "SUCCESSFUL" and summary.startswith(
                        lz_summary_prefix
                    ):
                        if lz and not lz.payment_method:
                            lz.payment_method = "karte"
                            lz.paid_at = datetime.now(timezone.utc)
                            lz.payment_transaction_id = item.get(
                                "transaction_code"
                            ) or item.get("id")
                            db.commit()
                            db.refresh(lz)
                        d = lz.to_dict()
                        materials = (
                            db.query(LaufzettelMaterial)
                            .filter(LaufzettelMaterial.laufzettel_id == lz.id)
                            .all()
                        )
                        d["material"] = [m.to_dict() for m in materials]
                        _schedule_pdf_upload(lz, materials)
                        _schedule_receipt_email(lz, materials, request)
                        from backend.buchhaltung.accounting import (
                            record_laufzettel_payment,
                        )

                        record_laufzettel_payment(lz, materials)
                        _pending_payments.pop(client_transaction_id, None)
                        # Push notification (non-critical)
                        try:
                            if send_push_notification:
                                send_push_notification(
                                    title="Zahlung eingegangen",
                                    body=f"Laufzettel #{laufzettel_id} — Kartenzahlung (SumUp)",
                                    tag=f"payment-{laufzettel_id}",
                                    url=f"/laufzettel/{laufzettel_id}",
                                )
                        except Exception:
                            pass
                        return {"status": "SUCCESSFUL", "laufzettel": d}
        except Exception:
            pass  # fall through to PENDING on network / API errors

    return {"status": pending["status"]}


@router.post("/api/laufzettel/{laufzettel_id}/pay/karte/confirm-mock")
async def confirm_mock_karte(
    laufzettel_id: int, request: Request, db: Session = Depends(get_db)
):
    """Confirm mock card payment"""
    from datetime import datetime, timezone

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(status_code=409, detail="Already paid")

    lz.payment_method = "karte"
    lz.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lz)
    d = lz.to_dict()
    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == lz.id)
        .all()
    )
    d["material"] = [m.to_dict() for m in materials]
    _schedule_pdf_upload(lz, materials)
    _schedule_receipt_email(lz, materials, request)
    from backend.buchhaltung.accounting import record_laufzettel_payment

    record_laufzettel_payment(lz, materials)
    # Push notification (non-critical)
    try:
        if send_push_notification:
            send_push_notification(
                title="Zahlung eingegangen",
                body=f"Laufzettel #{laufzettel_id} — Kartenzahlung (Mock)",
                tag=f"payment-{laufzettel_id}",
                url=f"/laufzettel/{laufzettel_id}",
            )
    except Exception:
        pass
    return d


@router.delete("/api/laufzettel/{laufzettel_id}/pay/karte")
async def cancel_karte_payment(
    laufzettel_id: int, client_transaction_id: str, db: Session = Depends(get_db)
):
    """Cancel pending card payment"""
    pending = _pending_payments.pop(client_transaction_id, None)
    return {"cancelled": pending is not None}


# In-memory store for pending hosted checkouts (checkout_id -> {laufzettel_id, created_at})
_pending_checkouts: dict = {}


@router.post("/api/laufzettel/{laufzettel_id}/pay/checkout")
async def pay_checkout_link(laufzettel_id: int, db: Session = Depends(get_db)):
    """Create a SumUp hosted checkout and return the customer-facing payment URL"""
    import uuid
    import httpx

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(status_code=409, detail="Already paid")
    if not (SUMUP_API_KEY and SUMUP_MERCHANT_CODE):
        raise HTTPException(
            status_code=503, detail="SumUp hosted checkout not configured"
        )

    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == laufzettel_id)
        .all()
    )
    _mat_total = sum(
        m.calculated_price for m in materials if m.calculated_price is not None
    )
    _, _credited = _calc_gutschein_totals(db, laufzettel_id)
    total = max(0.0, _mat_total - _credited)

    payload = {
        "checkout_reference": str(uuid.uuid4()),
        "amount": round(total, 2),
        "currency": "EUR",
        "merchant_code": SUMUP_MERCHANT_CODE,
        "description": f"Laufzettel #{laufzettel_id}",
        "hosted_checkout": {"enabled": True},
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.sumup.com/v0.1/checkouts",
            headers={"Authorization": f"Bearer {SUMUP_API_KEY}"},
            json=payload,
            timeout=15,
        )
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"SumUp API error: {r.text}")

    data = r.json()
    checkout_id = data["id"]
    _pending_checkouts[checkout_id] = {"laufzettel_id": laufzettel_id}

    return {
        "checkout_id": checkout_id,
        "checkout_url": data.get("hosted_checkout_url", ""),
        "amount": f"{total:.2f}",
        "valid_until": data.get("valid_until"),
        "status": "PENDING",
    }


@router.get("/api/laufzettel/{laufzettel_id}/pay/checkout/status")
async def get_checkout_status(
    laufzettel_id: int,
    checkout_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Poll SumUp for hosted checkout status; auto-confirms the Laufzettel when paid"""
    from datetime import datetime, timezone
    import httpx

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if lz and lz.payment_method == "karte":
        d = lz.to_dict()
        materials = (
            db.query(LaufzettelMaterial)
            .filter(LaufzettelMaterial.laufzettel_id == lz.id)
            .all()
        )
        d["material"] = [m.to_dict() for m in materials]
        return {"status": "PAID", "laufzettel": d}

    if not (SUMUP_API_KEY and SUMUP_MERCHANT_CODE):
        raise HTTPException(status_code=503, detail="SumUp not configured")

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.sumup.com/v0.1/checkouts/{checkout_id}",
            headers={"Authorization": f"Bearer {SUMUP_API_KEY}"},
            timeout=10,
        )
    if r.status_code == 404:
        return {"status": "NOT_FOUND"}
    if r.status_code != 200:
        return {"status": "ERROR"}

    sumup_status = r.json().get("status", "PENDING")

    if sumup_status == "PAID" and lz and not lz.payment_method:
        lz.payment_method = "karte"
        lz.paid_at = datetime.now(timezone.utc)
        lz.payment_transaction_id = checkout_id
        db.commit()
        db.refresh(lz)
        d = lz.to_dict()
        materials = (
            db.query(LaufzettelMaterial)
            .filter(LaufzettelMaterial.laufzettel_id == lz.id)
            .all()
        )
        d["material"] = [m.to_dict() for m in materials]
        _schedule_pdf_upload(lz, materials)
        _schedule_receipt_email(lz, materials, request)
        from backend.buchhaltung.accounting import record_laufzettel_payment

        record_laufzettel_payment(lz, materials)
        _pending_checkouts.pop(checkout_id, None)
        # Push notification (non-critical)
        try:
            if send_push_notification:
                send_push_notification(
                    title="Zahlung eingegangen",
                    body=f"Laufzettel #{laufzettel_id} — Kartenzahlung (Checkout)",
                    tag=f"payment-{laufzettel_id}",
                    url=f"/laufzettel/{laufzettel_id}",
                )
        except Exception:
            pass
        return {"status": "PAID", "laufzettel": d}

    return {"status": sumup_status}


@router.delete("/api/laufzettel/{laufzettel_id}/pay/checkout")
async def cancel_checkout(laufzettel_id: int, checkout_id: str):
    """Clean up a pending hosted checkout"""
    _pending_checkouts.pop(checkout_id, None)
    return {"cancelled": True}


@router.delete("/api/laufzettel/{laufzettel_id}/pay")
async def reset_payment(laufzettel_id: int, db: Session = Depends(get_db)):
    """Reset payment status (for admin corrections)"""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    lz.payment_method = None
    lz.paid_at = None
    lz.payment_transaction_id = None
    lz.payment_notes = None
    db.commit()
    db.refresh(lz)
    d = lz.to_dict()
    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == lz.id)
        .all()
    )
    d["material"] = [m.to_dict() for m in materials]
    return d


# ── Guest Access Helper ─────────────────────────────────────────────────────


def _check_guest_access(request: Request, lz: Laufzettel) -> bool:
    """Check if guest has access to this Laufzettel via session cookie"""
    guest_id = request.session.get("guest_id")
    if guest_id and lz.guest_id == guest_id:
        return True
    return False


def _calc_gutschein_totals(db: Session, laufzettel_id: int) -> tuple[list, float]:
    """Return (credits_list, total_credited) for a Laufzettel."""
    credits = (
        db.query(LaufzettelGutschein)
        .filter(LaufzettelGutschein.laufzettel_id == laufzettel_id)
        .all()
    )
    total_credited = round(sum(c.amount_debited for c in credits), 2)
    return credits, total_credited


def _enrich_with_gutschein(d: dict, db: Session, materials: list) -> dict:
    """Add gutschein_credits, total_credited, remaining_amount to a Laufzettel dict."""
    credits, total_credited = _calc_gutschein_totals(db, d["id"])
    mat_total = sum(
        m.calculated_price for m in materials if m.calculated_price is not None
    )
    d["gutschein_credits"] = [c.to_dict() for c in credits]
    d["total_credited"] = total_credited
    d["remaining_amount"] = round(max(0.0, mat_total - total_credited), 2)
    return d


# ── Guest Laufzettel API ─────────────────────────────────────────────────────


class GuestLaufzettelCreate(BaseModel):
    name: str
    address: str
    email: Optional[str] = None
    date: Optional[str] = None  # ISO date string
    start: Optional[str] = None  # ISO datetime


@router.get("/guest/laufzettel", response_class=HTMLResponse)
async def guest_laufzettel_page(request: Request):
    """Render guest Laufzettel form page (QR code landing)"""
    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse(
        "guest-laufzettel-form.html", {"request": request}
    )


@router.get("/api/guest/session-check")
async def guest_session_check(request: Request):
    """Check if guest has an active session"""
    guest_id = request.session.get("guest_id")
    if guest_id:
        return {"guest_id": guest_id}
    return {"guest_id": None}


@router.post("/api/guest/laufzettel")
async def create_guest_laufzettel(
    data: GuestLaufzettelCreate, request: Request, db: Session = Depends(get_db)
):
    """Create a new guest Laufzettel"""
    from datetime import datetime, date as dt_date, timezone
    import uuid
    import secrets

    # Generate guest_id (UUID)
    guest_id = str(uuid.uuid4())

    # Generate random UID for guest (GUEST-XXXXXX)
    guest_uid = f"GUEST-{secrets.token_hex(3).upper()}"

    # Parse date
    if data.date:
        try:
            entry_date = dt_date.fromisoformat(data.date)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid date format, use YYYY-MM-DD"},
            )
    else:
        entry_date = dt_date.today()

    # Parse start time
    start_dt = None
    if data.start:
        try:
            start_dt = datetime.fromisoformat(data.start)
        except ValueError:
            return JSONResponse(
                status_code=400, content={"detail": "Invalid start datetime format"}
            )
    else:
        start_dt = datetime.now(timezone.utc)

    # Check for existing unpaid Laufzettel for this guest today
    existing_open = (
        db.query(Laufzettel)
        .filter(
            Laufzettel.guest_id == guest_id,
            Laufzettel.date == entry_date,
            Laufzettel.payment_method.is_(None),
        )
        .first()
    )
    if existing_open:
        return JSONResponse(
            status_code=400,
            content={
                "detail": f"An open (unpaid) Laufzettel for today already exists (id={existing_open.id})"
            },
        )

    # Create Laufzettel
    lz = Laufzettel(
        uid=guest_uid,
        date=entry_date,
        start=start_dt,
        owner_name=data.name,
        guest_id=guest_id,
        guest_email=data.email,
        guest_address=data.address,
        nodes=json.dumps([]),
    )
    db.add(lz)
    db.commit()
    db.refresh(lz)

    # Set guest_id cookie
    request.session["guest_id"] = guest_id

    # Send emails (non-critical, fire-and-forget)
    if data.email:
        # Get materials for the new Laufzettel (should be empty at creation, but fetch anyway)
        materials = (
            db.query(LaufzettelMaterial)
            .filter(LaufzettelMaterial.laufzettel_id == lz.id)
            .order_by(LaufzettelMaterial.id)
            .all()
        )

        # 1. EasyVerein signup email
        if _send_email and easyverein_signup_html:
            try:
                from backend.config import EASYVEREIN_SIGNUP_URL

                html = easyverein_signup_html(data.name, EASYVEREIN_SIGNUP_URL)
                asyncio.create_task(
                    _send_email(
                        to=data.email,
                        subject="Willkommen in der H3cke! Jetzt Mitglied werden",
                        html_body=html,
                    )
                )
            except Exception:
                logger.exception(
                    "Failed to schedule easyVerein signup email for guest Laufzettel #%s",
                    lz.id,
                )

        # 2. Welcome email with direct link to view Laufzettel
        if _send_email and laufzettel_receipt_html:
            try:
                # Construct direct view URL
                from backend.config import PUBLIC_BASE_URL

                base = PUBLIC_BASE_URL or f"{request.url.scheme}://{request.url.netloc}"
                view_url = f"{base}/laufzettel/view/{lz.id}"

                html = laufzettel_receipt_html(lz, materials, view_url)
                asyncio.create_task(
                    _send_email(
                        to=data.email,
                        subject=f"Dein H3cke Laufzettel #{lz.id} ist erstellt!",
                        html_body=html,
                    )
                )
                logger.info(
                    "Sent welcome email with view link to %s for Laufzettel #%s",
                    data.email,
                    lz.id,
                )
            except Exception:
                logger.exception(
                    "Failed to schedule welcome email with view link for guest Laufzettel #%s",
                    lz.id,
                )

    d = lz.to_dict()
    d["material"] = []
    return d


@router.get("/api/guest/laufzettel/{guest_id}")
async def get_guest_laufzettel(guest_id: str, db: Session = Depends(get_db)):
    """Get the current unpaid Laufzettel for a guest"""
    from datetime import date as dt_date

    today = dt_date.today()
    lz = (
        db.query(Laufzettel)
        .filter(
            Laufzettel.guest_id == guest_id,
            Laufzettel.date == today,
            Laufzettel.payment_method.is_(None),
        )
        .first()
    )

    if not lz:
        raise HTTPException(
            status_code=404, detail="No unpaid Laufzettel found for today"
        )

    d = lz.to_dict()
    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == lz.id)
        .all()
    )
    d["material"] = [m.to_dict() for m in materials]
    return d


@router.get("/api/guest/laufzettel/{guest_id}/previous")
async def get_guest_previous_unpaid(guest_id: str, db: Session = Depends(get_db)):
    """Check for unpaid Laufzettel from previous days"""
    from datetime import date as dt_date

    today = dt_date.today()
    lz = (
        db.query(Laufzettel)
        .filter(
            Laufzettel.guest_id == guest_id,
            Laufzettel.date < today,
            Laufzettel.payment_method.is_(None),
        )
        .order_by(Laufzettel.date.desc())
        .first()
    )

    if not lz:
        return {"has_previous_unpaid": False}

    d = lz.to_dict()
    return {
        "has_previous_unpaid": True,
        "laufzettel": d,
    }


@router.get("/guest/laufzettel/{laufzettel_id}", response_class=HTMLResponse)
async def guest_laufzettel_detail_page(
    request: Request, laufzettel_id: int, db: Session = Depends(get_db)
):
    """Render guest Laufzettel detail page (simplified, no navigation)"""
    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")

    # Verify guest has access via cookie
    guest_id = request.session.get("guest_id")
    if not guest_id:
        return RedirectResponse("/guest/laufzettel", status_code=302)

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")

    if lz.guest_id != guest_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return templates.TemplateResponse(
        "guest-laufzettel-detail.html",
        {"request": request, "laufzettel_id": laufzettel_id},
    )


# ── Gutschein (Gift Card) Payment API ────────────────────────────────────────


class ApplyGutscheinRequest(BaseModel):
    shopify_gift_card_id: str
    last_chars: str
    amount: float
    note: str = ""


@router.post("/api/laufzettel/{laufzettel_id}/apply-gutschein")
async def apply_gutschein(
    laufzettel_id: int,
    body: ApplyGutscheinRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Apply a Shopify gift card credit to an open Laufzettel (partial or full payment)."""
    from datetime import datetime, timezone
    from backend.shopify.routes import _graphql_query

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(status_code=409, detail="Already paid")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == laufzettel_id)
        .all()
    )
    mat_total = sum(
        m.calculated_price for m in materials if m.calculated_price is not None
    )
    existing_credits, total_credited = _calc_gutschein_totals(db, laufzettel_id)
    remaining = round(mat_total - total_credited, 2)

    if body.amount > remaining + 0.005:
        raise HTTPException(
            status_code=400,
            detail=f"Amount {body.amount:.2f} € exceeds remaining balance {remaining:.2f} €",
        )

    amount_to_debit = round(min(body.amount, remaining), 2)
    gid = f"gid://shopify/GiftCard/{body.shopify_gift_card_id}"
    mutation = """
    mutation($id: ID!, $amount: MoneyInput!, $note: String) {
      giftCardDebit(id: $id, debitInput: {debitAmount: $amount, note: $note}) {
        giftCardDebitTransaction { id amount { amount currencyCode } }
        userErrors { field message }
      }
    }
    """
    variables = {
        "id": gid,
        "amount": {"amount": str(amount_to_debit), "currencyCode": "EUR"},
        "note": body.note or f"Laufzettel #{laufzettel_id}",
    }

    try:
        result_data = await _graphql_query(mutation, variables)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Shopify API error: {exc}")

    gc_result = result_data.get("giftCardDebit", {})
    errors = gc_result.get("userErrors", [])
    if errors:
        msgs = "; ".join(e.get("message", "") for e in errors)
        raise HTTPException(status_code=400, detail=f"Shopify: {msgs}")

    tx_id = (gc_result.get("giftCardDebitTransaction") or {}).get("id")

    credit = LaufzettelGutschein(
        laufzettel_id=laufzettel_id,
        shopify_gift_card_id=body.shopify_gift_card_id,
        last_chars=body.last_chars,
        amount_debited=amount_to_debit,
        transaction_id=tx_id,
        applied_at=datetime.now(timezone.utc),
        applied_by=request.session.get("user"),
        note=body.note or None,
    )
    db.add(credit)

    # Auto-lock if fully covered by gift cards
    new_remaining = round(remaining - amount_to_debit, 2)
    if new_remaining <= 0.005:
        lz.payment_method = "gutschein"
        lz.paid_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        # Compensating credit to undo the Shopify debit
        try:
            refund_mut = """
            mutation($id: ID!, $amount: MoneyInput!, $note: String) {
              giftCardCredit(id: $id, creditInput: {creditAmount: $amount, note: $note}) {
                giftCardCreditTransaction { amount { amount } }
                userErrors { field message }
              }
            }
            """
            await _graphql_query(
                refund_mut,
                {
                    "id": gid,
                    "amount": {"amount": str(amount_to_debit), "currencyCode": "EUR"},
                    "note": "Rollback: DB commit failed",
                },
            )
        except Exception:
            logger.error(
                "CRITICAL: Shopify debit rollback failed for GC %s amount %.2f — manual refund required",
                body.shopify_gift_card_id,
                amount_to_debit,
            )
        raise HTTPException(status_code=500, detail="Failed to record gift card credit")

    db.refresh(lz)

    # If fully paid by gift cards, fire post-payment side effects
    if lz.payment_method == "gutschein":
        _schedule_pdf_upload(lz, materials)
        _schedule_receipt_email(lz, materials, request)
        from backend.buchhaltung.accounting import record_laufzettel_payment

        record_laufzettel_payment(lz, materials)
        try:
            if send_push_notification:
                send_push_notification(
                    title="Zahlung eingegangen",
                    body=f"Laufzettel #{laufzettel_id} — Gutschein-Zahlung",
                    tag=f"payment-{laufzettel_id}",
                    url=f"/laufzettel/{laufzettel_id}",
                )
        except Exception:
            pass

    d = lz.to_dict()
    d["material"] = [m.to_dict() for m in materials]
    _enrich_with_gutschein(d, db, materials)
    return d


@router.delete("/api/laufzettel/{laufzettel_id}/gutschein/{gutschein_id}")
async def remove_gutschein(
    laufzettel_id: int,
    gutschein_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Remove an applied gift card credit and refund it back to Shopify (admin only)."""
    from backend.auth.dependencies import is_admin_verified
    from backend.shopify.routes import _graphql_query

    if not is_admin_verified(request):
        raise HTTPException(status_code=403, detail="Admin verification required")

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method and lz.payment_method != "gutschein":
        raise HTTPException(
            status_code=409,
            detail="Cannot remove a gift card credit after payment by another method",
        )

    credit = (
        db.query(LaufzettelGutschein)
        .filter(
            LaufzettelGutschein.id == gutschein_id,
            LaufzettelGutschein.laufzettel_id == laufzettel_id,
        )
        .first()
    )
    if not credit:
        raise HTTPException(status_code=404, detail="Gift card credit not found")

    # Refund the debited amount back to the Shopify gift card
    gid = f"gid://shopify/GiftCard/{credit.shopify_gift_card_id}"
    refund_mut = """
    mutation($id: ID!, $amount: MoneyInput!, $note: String) {
      giftCardCredit(id: $id, creditInput: {creditAmount: $amount, note: $note}) {
        giftCardCreditTransaction { amount { amount } }
        userErrors { field message }
      }
    }
    """
    try:
        result_data = await _graphql_query(
            refund_mut,
            {
                "id": gid,
                "amount": {"amount": str(credit.amount_debited), "currencyCode": "EUR"},
                "note": f"Stornierung: Laufzettel #{laufzettel_id}",
            },
        )
        errors = (result_data.get("giftCardCredit") or {}).get("userErrors", [])
        if errors:
            msgs = "; ".join(e.get("message", "") for e in errors)
            raise HTTPException(
                status_code=400, detail=f"Shopify refund failed: {msgs}"
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Shopify API error: {exc}")

    db.delete(credit)

    # Unlock if the Laufzettel was paid only by gift cards
    if lz.payment_method == "gutschein":
        lz.payment_method = None
        lz.paid_at = None

    db.commit()
    return {"success": True, "refunded": credit.amount_debited}


# ── Wero Payment API ────────────────────────────────────────────────────────

# In-memory store for pending Wero payments (checkout_id -> {laufzettel_id, created_at, status})
_pending_wero_payments: dict = {}


@router.post("/api/laufzettel/{laufzettel_id}/pay/wero")
async def pay_wero(laufzettel_id: int, request: Request, db: Session = Depends(get_db)):
    """Initiate Wero payment - returns QR code URL for customer scan"""
    from datetime import datetime, timezone, timedelta
    import uuid

    if not WERO_ENABLED:
        raise HTTPException(status_code=503, detail="Wero payment not enabled")

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(status_code=409, detail="Already paid")

    # Calculate remaining amount (material total minus any applied gift card credits)
    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == laufzettel_id)
        .all()
    )
    _mat_total = sum(
        m.calculated_price for m in materials if m.calculated_price is not None
    )
    _, _credited = _calc_gutschein_totals(db, laufzettel_id)
    total = max(0.0, _mat_total - _credited)
    amount_str = f"{total:.2f}"

    # Generate checkout ID
    checkout_id = str(uuid.uuid4())

    if WERO_MOCK:
        # Mock mode: simulate Wero payment flow
        _pending_wero_payments[checkout_id] = {
            "laufzettel_id": laufzettel_id,
            "created_at": datetime.now(timezone.utc),
            "status": "PENDING",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "amount": amount_str,
            "mock": True,
        }
        # Generate a mock QR code URL (would be a real Wero link in production)
        mock_payment_url = (
            f"wero://pay?amount={amount_str}&currency=EUR&checkout={checkout_id}"
        )
        return {
            "mock": True,
            "checkout_id": checkout_id,
            "payment_url": mock_payment_url,
            "amount": amount_str,
            "status": "PENDING",
            "expires_at": _pending_wero_payments[checkout_id]["expires_at"].isoformat(),
        }

    # Real Wero API integration (to be implemented when credentials available)
    # This would call the Wero API to create a payment request
    raise HTTPException(
        status_code=501, detail="Wero API integration not yet implemented"
    )


@router.get("/api/laufzettel/{laufzettel_id}/pay/wero/status")
async def get_wero_status(
    laufzettel_id: int,
    checkout_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Check status of Wero payment"""
    from datetime import datetime, timezone

    # Check if already paid directly
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if lz and lz.payment_method == "wero":
        d = lz.to_dict()
        materials = (
            db.query(LaufzettelMaterial)
            .filter(LaufzettelMaterial.laufzettel_id == lz.id)
            .all()
        )
        d["material"] = [m.to_dict() for m in materials]
        return {"status": "PAID", "laufzettel": d}

    # Check pending payments
    pending = _pending_wero_payments.get(checkout_id)
    if not pending:
        return {"status": "NOT_FOUND"}

    # Check timeout
    if datetime.now(timezone.utc) > pending["expires_at"]:
        del _pending_wero_payments[checkout_id]
        return {"status": "TIMEOUT"}

    # Mock mode: auto-confirm after 3 seconds (for testing)
    if pending.get("mock") and pending["status"] == "PENDING":
        elapsed = (datetime.now(timezone.utc) - pending["created_at"]).total_seconds()
        if elapsed > 3:
            # Auto-confirm in mock mode
            if lz and not lz.payment_method:
                lz.payment_method = "wero"
                lz.paid_at = datetime.now(timezone.utc)
                lz.payment_transaction_id = f"WERO-MOCK-{checkout_id[:8]}"
                db.commit()
                db.refresh(lz)
            d = lz.to_dict()
            materials = (
                db.query(LaufzettelMaterial)
                .filter(LaufzettelMaterial.laufzettel_id == lz.id)
                .all()
            )
            d["material"] = [m.to_dict() for m in materials]
            _schedule_pdf_upload(lz, materials)
            _schedule_receipt_email(lz, materials, request)
            from backend.buchhaltung.accounting import record_laufzettel_payment

            record_laufzettel_payment(lz, materials)
            _pending_wero_payments.pop(checkout_id, None)
            # Push notification (non-critical)
            try:
                if send_push_notification:
                    send_push_notification(
                        title="Zahlung eingegangen",
                        body=f"Laufzettel #{laufzettel_id} — Wero-Zahlung (Auto/Mock)",
                        tag=f"payment-{laufzettel_id}",
                        url=f"/laufzettel/{laufzettel_id}",
                    )
            except Exception:
                pass
            return {"status": "PAID", "laufzettel": d}

    return {"status": pending["status"]}


@router.post("/api/laufzettel/{laufzettel_id}/pay/wero/confirm")
async def confirm_wero_payment(
    laufzettel_id: int,
    checkout_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Manually confirm Wero payment (for mock mode or when webhook fails)"""
    from datetime import datetime, timezone

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(status_code=409, detail="Already paid")

    pending = _pending_wero_payments.get(checkout_id)
    if pending and pending.get("laufzettel_id") != laufzettel_id:
        raise HTTPException(
            status_code=400, detail="Checkout ID does not match Laufzettel"
        )

    lz.payment_method = "wero"
    lz.paid_at = datetime.now(timezone.utc)
    lz.payment_transaction_id = f"WERO-{checkout_id[:8]}" if pending else None
    db.commit()
    db.refresh(lz)

    # Clean up pending
    if checkout_id in _pending_wero_payments:
        del _pending_wero_payments[checkout_id]

    d = lz.to_dict()
    materials = (
        db.query(LaufzettelMaterial)
        .filter(LaufzettelMaterial.laufzettel_id == lz.id)
        .all()
    )
    d["material"] = [m.to_dict() for m in materials]
    _schedule_pdf_upload(lz, materials)
    _schedule_receipt_email(lz, materials, request)
    from backend.buchhaltung.accounting import record_laufzettel_payment

    record_laufzettel_payment(lz, materials)

    # Push notification (non-critical)
    try:
        if send_push_notification:
            send_push_notification(
                title="Zahlung eingegangen",
                body=f"Laufzettel #{laufzettel_id} – Wero-Zahlung",
                tag=f"payment-{laufzettel_id}",
                url=f"/laufzettel/{laufzettel_id}",
            )
    except Exception:
        pass
    return d


# ── Public View (No Auth Required) ──────────────────────────────────────────────


@router.get("/laufzettel/view/{laufzettel_id}", response_class=HTMLResponse)
async def public_laufzettel_view(laufzettel_id: int, request: Request):
    """Public, read-only view of a Laufzettel (no authentication required)."""
    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")

    # Fetch Laufzettel
    db: Session = next(get_db())
    try:
        lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
        if not lz:
            raise HTTPException(status_code=404, detail="Laufzettel nicht gefunden")

        # Fetch materials
        materials = (
            db.query(LaufzettelMaterial)
            .filter(LaufzettelMaterial.laufzettel_id == lz.id)
            .order_by(LaufzettelMaterial.id)
            .all()
        )

        # Build variante_id -> location_name map from catalog DB
        variante_ids = [m.variante_id for m in materials if m.variante_id]
        location_map: dict[int, str] = {}
        if variante_ids:
            try:
                from backend.catalog.db import SessionLocal as CatalogSession
                from backend.catalog.models import (
                    Location,
                    MaterialKategorie,
                    MaterialVariante,
                )

                cat_db = CatalogSession()
                try:
                    rows = (
                        cat_db.query(MaterialVariante, MaterialKategorie, Location)
                        .join(
                            MaterialKategorie,
                            MaterialVariante.kategorie_id == MaterialKategorie.id,
                        )
                        .join(Location, MaterialKategorie.location_id == Location.id)
                        .filter(MaterialVariante.id.in_(variante_ids))
                        .all()
                    )
                    for v, _k, loc in rows:
                        location_map[v.id] = loc.name
                finally:
                    cat_db.close()
            except Exception:
                pass  # location grouping is optional; don't crash if catalog unavailable

        # Prepare materials data with calculated prices
        materials_data = []
        for mat in materials:
            materials_data.append(
                {
                    "name": mat.name or "—",
                    "quantity": mat.menge,
                    "unit": mat.unit,
                    "price": mat.calculated_price
                    if mat.calculated_price is not None
                    else 0.0,
                    "tax_rate": mat.tax_rate,
                    "location": location_map.get(mat.variante_id)
                    if mat.variante_id
                    else None,
                }
            )

        # Pre-format datetimes — SQLite may return strings instead of datetime
        # objects for timezone-aware columns, so we normalise here.
        from backend.laufzettel.models import _naive_to_utc as _lz_utc
        import datetime as _dt

        def _fmt(val, fmt):
            if val is None:
                return None
            if isinstance(val, str):
                # SQLite sometimes returns the raw ISO string
                try:
                    val = _dt.datetime.fromisoformat(val.replace("Z", "+00:00"))
                except ValueError:
                    return val
            val = _lz_utc(val)
            return val.strftime(fmt)

        return templates.TemplateResponse(
            "public-laufzettel.html",
            {
                "request": request,
                "laufzettel": lz,
                "materials": materials_data,
                "start_str": _fmt(lz.start, "%H:%M"),
                "paid_at_str": _fmt(lz.paid_at, "%d.%m.%Y um %H:%M"),
                "date_str": lz.date.strftime("%d.%m.%Y") if lz.date else "—",
            },
        )
    finally:
        db.close()


@router.delete("/api/laufzettel/{laufzettel_id}/pay/wero")
async def cancel_wero_payment(laufzettel_id: int, checkout_id: str):
    """Cancel pending Wero payment"""
    pending = _pending_wero_payments.pop(checkout_id, None)
    return {"cancelled": pending is not None}

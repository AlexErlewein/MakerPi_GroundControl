"""Laufzettel routes - API and pages for work orders"""

from typing import Optional
from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json

from .db import get_db, init_db
from .models import Laufzettel, LaufzettelMaterial

router = APIRouter()


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
    return templates.TemplateResponse("laufzettel.html", {"request": request})


@router.get("/laufzettel/{laufzettel_id}", response_class=HTMLResponse)
async def laufzettel_detail_page(request: Request, laufzettel_id: int, db: Session = Depends(get_db)):
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
        "laufzettel-detail.html", {"request": request, "laufzettel_id": laufzettel_id}
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
            return JSONResponse(status_code=400, content={"detail": "Invalid date format, use YYYY-MM-DD"})
    else:
        entry_date = dt_date.today()

    existing_open = db.query(Laufzettel).filter(
        Laufzettel.uid == uid,
        Laufzettel.date == entry_date,
        Laufzettel.payment_method == None,
    ).first()
    if existing_open:
        return JSONResponse(status_code=400, content={"detail": f"An open (unpaid) Laufzettel for {uid} on {entry_date} already exists (id={existing_open.id})"})

    start_dt = None
    if data.start:
        try:
            start_dt = datetime.fromisoformat(data.start)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid start datetime format"})

    # Auto-resolve owner_name and mitglied_id from Mitglied.nfc_uid if not provided
    resolved_mitglied_id = data.member_id  # keep string member_id for legacy
    resolved_mitglied_db_id = None
    resolved_owner_name = data.owner_name
    try:
        from backend.members.db import SessionLocal as MembersSession
        from backend.members.models import Mitglied, RFIDTag
        members_db = MembersSession()
        try:
            mitglied = members_db.query(Mitglied).filter(Mitglied.nfc_uid == uid).first()
            if mitglied:
                resolved_mitglied_db_id = mitglied.id
                if not resolved_owner_name:
                    resolved_owner_name = mitglied.name
                if not resolved_mitglied_id:
                    resolved_mitglied_id = mitglied.member_id
            else:
                tag = members_db.query(RFIDTag).filter(RFIDTag.uid == uid, RFIDTag.active == 1).first()
                if tag:
                    if not resolved_owner_name:
                        resolved_owner_name = tag.owner_name
                    if not resolved_mitglied_id:
                        resolved_mitglied_id = tag.member_id
                    if tag.member_id:
                        m = members_db.query(Mitglied).filter(Mitglied.member_id == tag.member_id).first()
                        if m:
                            resolved_mitglied_db_id = m.id
        finally:
            members_db.close()
    except Exception:
        pass

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
async def get_laufzettel(uid: Optional[str] = None, date: Optional[str] = None, db: Session = Depends(get_db)):
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
            return JSONResponse(status_code=400, content={"detail": "Invalid date format, use YYYY-MM-DD"})
    entries = query.order_by(Laufzettel.date.desc(), Laufzettel.start.desc()).all()
    result = []
    for lz in entries:
        d = lz.to_dict()
        materials = db.query(LaufzettelMaterial).filter(
            LaufzettelMaterial.laufzettel_id == lz.id
        ).all()
        d["material"] = [m.to_dict() for m in materials]
        result.append(d)
    return result


@router.get("/api/laufzettel/{laufzettel_id}")
async def get_laufzettel_detail(laufzettel_id: int, db: Session = Depends(get_db)):
    """Get a single Laufzettel with its material entries"""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    d = lz.to_dict()
    materials = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.laufzettel_id == lz.id
    ).all()
    d["material"] = [m.to_dict() for m in materials]
    return d


@router.get("/api/tags/{uid}/laufzettel")
async def get_laufzettel_for_tag(uid: str, db: Session = Depends(get_db)):
    """Get all Laufzettel entries for a specific tag"""
    entries = db.query(Laufzettel).filter(
        Laufzettel.uid == uid.upper()
    ).order_by(Laufzettel.date.desc()).all()
    result = []
    for lz in entries:
        d = lz.to_dict()
        materials = db.query(LaufzettelMaterial).filter(
            LaufzettelMaterial.laufzettel_id == lz.id
        ).all()
        d["material"] = [m.to_dict() for m in materials]
        result.append(d)
    return result


@router.put("/api/laufzettel/{laufzettel_id}")
async def update_laufzettel(laufzettel_id: int, data: LaufzettelUpdate, db: Session = Depends(get_db)):
    """Update editable fields of a Laufzettel"""
    from datetime import datetime
    
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(status_code=409, detail="Laufzettel is already paid and locked")
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
    materials = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.laufzettel_id == lz.id
    ).all()
    d["material"] = [m.to_dict() for m in materials]
    return d


@router.post("/api/laufzettel/{laufzettel_id}/material")
async def add_material(laufzettel_id: int, mat: MaterialCreate, db: Session = Depends(get_db)):
    """Add a material entry to a Laufzettel"""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(status_code=409, detail="Laufzettel is already paid and locked")
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
    db.add(new_mat)
    db.commit()
    db.refresh(new_mat)
    return new_mat.to_dict()


@router.put("/api/laufzettel/{laufzettel_id}/material/{material_id}")
async def update_material(
    laufzettel_id: int, material_id: int, mat: MaterialUpdate, db: Session = Depends(get_db)
):
    """Update a material entry"""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if lz and lz.payment_method:
        raise HTTPException(status_code=409, detail="Laufzettel is already paid and locked")
    existing = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.id == material_id,
        LaufzettelMaterial.laufzettel_id == laufzettel_id,
    ).first()
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
    db.commit()
    db.refresh(existing)
    return existing.to_dict()


@router.delete("/api/laufzettel/{laufzettel_id}/material/{material_id}")
async def delete_material(laufzettel_id: int, material_id: int, db: Session = Depends(get_db)):
    """Delete a material entry"""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if lz and lz.payment_method:
        raise HTTPException(status_code=409, detail="Laufzettel is already paid and locked")
    mat = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.id == material_id,
        LaufzettelMaterial.laufzettel_id == laufzettel_id,
    ).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material entry not found")
    db.delete(mat)
    db.commit()
    return {"success": True}


# ── Payment API ───────────────────────────────────────────────────────────────

from backend.config import SUMUP_API_KEY, SUMUP_MERCHANT_CODE, SUMUP_READER_ID, SUMUP_AFFILIATE_KEY, SUMUP_MOCK


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
    }


class BarPayRequest(BaseModel):
    notes: str = ""


@router.post("/api/laufzettel/{laufzettel_id}/pay/bar")
async def pay_bar(laufzettel_id: int, body: BarPayRequest = BarPayRequest(), db: Session = Depends(get_db)):
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
    materials = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.laufzettel_id == lz.id
    ).all()
    d["material"] = [m.to_dict() for m in materials]
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

    # Calculate total from material entries
    materials = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.laufzettel_id == laufzettel_id
    ).all()
    total = sum(m.calculated_price for m in materials if m.calculated_price is not None)
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
            } if SUMUP_AFFILIATE_KEY else None,
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

    raise HTTPException(status_code=503, detail="Keine SumUp-Zahlungsmethode konfiguriert")


@router.get("/api/laufzettel/{laufzettel_id}/pay/karte/status")
async def get_karte_status(
    laufzettel_id: int,
    client_transaction_id: str,
    db: Session = Depends(get_db)
):
    """Check status of card payment"""
    from datetime import datetime, timezone
    
    # Check if already paid directly
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if lz and lz.payment_method == "karte":
        d = lz.to_dict()
        materials = db.query(LaufzettelMaterial).filter(
            LaufzettelMaterial.laufzettel_id == lz.id
        ).all()
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
                    if (
                        item.get("status") == "SUCCESSFUL"
                        and summary.startswith(lz_summary_prefix)
                    ):
                        if lz and not lz.payment_method:
                            lz.payment_method = "karte"
                            lz.paid_at = datetime.now(timezone.utc)
                            lz.payment_transaction_id = item.get("transaction_code") or item.get("id")
                            db.commit()
                            db.refresh(lz)
                        d = lz.to_dict()
                        materials = db.query(LaufzettelMaterial).filter(
                            LaufzettelMaterial.laufzettel_id == lz.id
                        ).all()
                        d["material"] = [m.to_dict() for m in materials]
                        _pending_payments.pop(client_transaction_id, None)
                        return {"status": "SUCCESSFUL", "laufzettel": d}
        except Exception:
            pass  # fall through to PENDING on network / API errors

    return {"status": pending["status"]}


@router.post("/api/laufzettel/{laufzettel_id}/pay/karte/confirm-mock")
async def confirm_mock_karte(laufzettel_id: int, db: Session = Depends(get_db)):
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
    materials = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.laufzettel_id == lz.id
    ).all()
    d["material"] = [m.to_dict() for m in materials]
    return d


@router.delete("/api/laufzettel/{laufzettel_id}/pay/karte")
async def cancel_karte_payment(laufzettel_id: int, client_transaction_id: str, db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=503, detail="SumUp hosted checkout not configured")

    materials = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.laufzettel_id == laufzettel_id
    ).all()
    total = sum(m.calculated_price for m in materials if m.calculated_price is not None)

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
    db: Session = Depends(get_db),
):
    """Poll SumUp for hosted checkout status; auto-confirms the Laufzettel when paid"""
    from datetime import datetime, timezone
    import httpx

    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if lz and lz.payment_method == "karte":
        d = lz.to_dict()
        materials = db.query(LaufzettelMaterial).filter(
            LaufzettelMaterial.laufzettel_id == lz.id
        ).all()
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
        materials = db.query(LaufzettelMaterial).filter(
            LaufzettelMaterial.laufzettel_id == lz.id
        ).all()
        d["material"] = [m.to_dict() for m in materials]
        _pending_checkouts.pop(checkout_id, None)
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
    materials = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.laufzettel_id == lz.id
    ).all()
    d["material"] = [m.to_dict() for m in materials]
    return d

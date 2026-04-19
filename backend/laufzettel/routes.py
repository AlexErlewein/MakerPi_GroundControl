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


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    menge: Optional[float] = None
    variante_id: Optional[int] = None
    unit: Optional[str] = None
    laenge_cm: Optional[float] = None
    breite_cm: Optional[float] = None
    hoehe_cm: Optional[float] = None
    calculated_price: Optional[float] = None


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
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("laufzettel.html", {"request": request})


@router.get("/laufzettel/{laufzettel_id}", response_class=HTMLResponse)
async def laufzettel_detail_page(request: Request, laufzettel_id: int, db: Session = Depends(get_db)):
    """Render Laufzettel detail/edit page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth
    
    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/login", status_code=302)
    
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

    existing = db.query(Laufzettel).filter(
        Laufzettel.uid == uid,
        Laufzettel.date == entry_date,
    ).first()
    if existing:
        return JSONResponse(status_code=400, content={"detail": f"Laufzettel for {uid} on {entry_date} already exists"})

    start_dt = None
    if data.start:
        try:
            start_dt = datetime.fromisoformat(data.start)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid start datetime format"})

    lz = Laufzettel(
        uid=uid,
        date=entry_date,
        start=start_dt,
        owner_name=data.owner_name,
        member_id=data.member_id,
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

from backend.config import SUMUP_API_KEY, SUMUP_MERCHANT_CODE, SUMUP_READER_ID, SUMUP_MOCK


@router.get("/api/payment/config")
async def get_payment_config():
    """Return payment configuration for frontend"""
    sumup_configured = bool(SUMUP_API_KEY and SUMUP_MERCHANT_CODE)
    return {
        "sumup_configured": sumup_configured,
        "sumup_mock": SUMUP_MOCK,
        "reader_id": SUMUP_READER_ID if sumup_configured else None,
    }


@router.post("/api/laufzettel/{laufzettel_id}/pay/bar")
async def pay_bar(laufzettel_id: int, db: Session = Depends(get_db)):
    """Mark Laufzettel as paid with cash"""
    from datetime import datetime, timezone
    
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    if lz.payment_method:
        raise HTTPException(status_code=409, detail="Already paid")
    lz.payment_method = "bar"
    lz.paid_at = datetime.now(timezone.utc)
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
    
    # TODO: Integrate with SumUp API if configured
    # For now, create pending payment that will timeout after 1 minute
    _pending_payments[txn_id] = {
        "laufzettel_id": laufzettel_id,
        "created_at": datetime.now(timezone.utc),
        "status": "PENDING",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=1),
    }
    
    return {
        "mock": False,
        "client_transaction_id": txn_id,
        "status": "PENDING",
    }


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


@router.delete("/api/laufzettel/{laufzettel_id}/pay")
async def reset_payment(laufzettel_id: int, db: Session = Depends(get_db)):
    """Reset payment status (for admin corrections)"""
    lz = db.query(Laufzettel).filter(Laufzettel.id == laufzettel_id).first()
    if not lz:
        raise HTTPException(status_code=404, detail="Laufzettel not found")
    lz.payment_method = None
    lz.paid_at = None
    db.commit()
    db.refresh(lz)
    d = lz.to_dict()
    materials = db.query(LaufzettelMaterial).filter(
        LaufzettelMaterial.laufzettel_id == lz.id
    ).all()
    d["material"] = [m.to_dict() for m in materials]
    return d

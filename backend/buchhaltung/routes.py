from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional
from .db import get_db, init_db
from .models import Verkauf, Spende
from backend.auth.dependencies import check_auth

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.on_event("startup")
async def startup():
    init_db()


@router.get("/buchhaltung", response_class=HTMLResponse)
async def buchhaltung_page(request: Request):
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("buchhaltung.html", {"request": request})


@router.get("/api/buchhaltung/summary")
async def get_summary(
    period: str = Query("month", pattern="^(week|month|year)$"),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    if period == "week":
        cutoff = now - timedelta(days=7)
    elif period == "year":
        cutoff = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    verkaufe = db.query(Verkauf).filter(Verkauf.paid_at >= cutoff).all()
    spenden = db.query(Spende).filter(Spende.date >= cutoff).all()

    material_total = sum(v.calculated_price for v in verkaufe)
    spende_total = sum(s.amount for s in spenden)

    by_variant: dict = {}
    for v in verkaufe:
        key = v.variante_name
        if key not in by_variant:
            by_variant[key] = {
                "name": key,
                "variante_id": v.variante_id,
                "units": 0.0,
                "revenue": 0.0,
                "pricing_model": v.pricing_model,
                "unit": v.unit,
            }
        by_variant[key]["units"] += v.menge or 1.0
        by_variant[key]["revenue"] += v.calculated_price

    return {
        "period": period,
        "cutoff": cutoff.isoformat(),
        "material_total": round(material_total, 2),
        "spende_total": round(spende_total, 2),
        "total": round(material_total + spende_total, 2),
        "by_variant": sorted(by_variant.values(), key=lambda x: x["revenue"], reverse=True),
        "spenden": [s.to_dict() for s in sorted(spenden, key=lambda x: x.date, reverse=True)],
        "verkauf_count": len(verkaufe),
        "spende_count": len(spenden),
    }


class SpendeCreate(BaseModel):
    amount: float
    donor_name: Optional[str] = None
    date: Optional[str] = None
    notes: Optional[str] = None


@router.post("/api/buchhaltung/spende")
async def create_spende(data: SpendeCreate, request: Request, db: Session = Depends(get_db)):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    date = datetime.fromisoformat(data.date) if data.date else datetime.now(timezone.utc)
    s = Spende(
        amount=data.amount,
        donor_name=data.donor_name or None,
        date=date,
        notes=data.notes or None,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.to_dict()


@router.delete("/api/buchhaltung/spende/{spende_id}")
async def delete_spende(spende_id: int, request: Request, db: Session = Depends(get_db)):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    s = db.query(Spende).filter(Spende.id == spende_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Spende not found")
    db.delete(s)
    db.commit()
    return {"success": True}

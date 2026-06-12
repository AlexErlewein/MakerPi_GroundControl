from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import check_auth

from .db import get_db, init_db
from .models import Spende, Verkauf

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.on_event("startup")
async def startup():
    init_db()


@router.get("/buchhaltung", response_class=HTMLResponse)
async def buchhaltung_page(request: Request):
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "buchhaltung.html",
        {
            "request": request,
            "nav_active": "buchhaltung",
            "current_user": request.session.get("user"),
        },
    )


@router.get("/api/buchhaltung/summary")
async def get_summary(
    request: Request,
    period: str = Query("month", pattern="^(week|month|year)$"),
    reference_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    now = datetime.now(timezone.utc)
    if reference_date:
        try:
            ref = datetime.fromisoformat(reference_date).replace(tzinfo=timezone.utc)
        except ValueError:
            ref = now
    else:
        ref = now

    if period == "week":
        # Monday of the week containing ref
        monday = ref - timedelta(days=ref.weekday())
        cutoff = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = cutoff + timedelta(days=7)
    elif period == "year":
        cutoff = ref.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = cutoff.replace(year=cutoff.year + 1)
    else:  # month
        cutoff = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if cutoff.month == 12:
            end = cutoff.replace(year=cutoff.year + 1, month=1)
        else:
            end = cutoff.replace(month=cutoff.month + 1)

    verkaufe = (
        db.query(Verkauf).filter(Verkauf.paid_at >= cutoff, Verkauf.paid_at < end).all()
    )
    spenden = db.query(Spende).filter(Spende.date >= cutoff, Spende.date < end).all()

    material_total = sum(v.calculated_price for v in verkaufe)
    spende_total = sum(s.amount for s in spenden)

    by_variant: dict = {}
    for v in verkaufe:
        key = v.variante_name
        if key not in by_variant:
            tax = v.tax_rate if v.tax_rate is not None else 19.0
            is_spende = bool(v.is_spende) if v.is_spende is not None else False
            by_variant[key] = {
                "name": key,
                "variante_id": v.variante_id,
                "units": 0.0,
                "revenue": 0.0,
                "pricing_model": v.pricing_model,
                "unit": v.unit,
                "tax_rate": tax,
                "is_spende": is_spende,
            }
        by_variant[key]["units"] += v.menge or 1.0
        by_variant[key]["revenue"] += v.calculated_price

    tax_buckets: dict = {
        19.0: [],
        7.0: [],
        0.0: [],
        "spende_katalog": [],
        "spende_laufzettel": [],
    }
    tax_totals: dict = {
        19.0: 0.0,
        7.0: 0.0,
        0.0: 0.0,
        "spende_katalog": 0.0,
        "spende_laufzettel": 0.0,
    }
    for variant in by_variant.values():
        if variant["is_spende"]:
            # Split: catalog items have variante_id, hardcoded Laufzettel Spenden don't
            if variant["variante_id"] is not None:
                tax_buckets["spende_katalog"].append(variant)
                tax_totals["spende_katalog"] += variant["revenue"]
            else:
                tax_buckets["spende_laufzettel"].append(variant)
                tax_totals["spende_laufzettel"] += variant["revenue"]
        else:
            bucket = variant["tax_rate"] if variant["tax_rate"] in tax_buckets else 19.0
            tax_buckets[bucket].append(variant)
            tax_totals[bucket] += variant["revenue"]

    return {
        "period": period,
        "cutoff": cutoff.isoformat(),
        "end": end.isoformat(),
        "material_total": round(material_total, 2),
        "spende_total": round(spende_total, 2),
        "total": round(material_total + spende_total, 2),
        "by_variant": sorted(
            by_variant.values(), key=lambda x: x["revenue"], reverse=True
        ),
        "tax_groups": {
            "19": sorted(tax_buckets[19.0], key=lambda x: x["revenue"], reverse=True),
            "7": sorted(tax_buckets[7.0], key=lambda x: x["revenue"], reverse=True),
            "0": sorted(tax_buckets[0.0], key=lambda x: x["revenue"], reverse=True),
            "spende_katalog": sorted(
                tax_buckets["spende_katalog"], key=lambda x: x["revenue"], reverse=True
            ),
            "spende_laufzettel": sorted(
                tax_buckets["spende_laufzettel"],
                key=lambda x: x["revenue"],
                reverse=True,
            ),
        },
        "tax_totals": {
            "19": round(tax_totals[19.0], 2),
            "7": round(tax_totals[7.0], 2),
            "0": round(tax_totals[0.0], 2),
            "spende_katalog": round(tax_totals["spende_katalog"], 2),
            "spende_laufzettel": round(tax_totals["spende_laufzettel"], 2),
        },
        "spenden": [
            s.to_dict() for s in sorted(spenden, key=lambda x: x.date, reverse=True)
        ],
        "verkauf_count": len(verkaufe),
        "spende_count": len(spenden),
    }


@router.get("/api/buchhaltung/spenden-total")
async def get_spenden_total(
    request: Request,
    period: str = Query("month", pattern="^(week|month|year)$"),
    reference_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get total donations for a period (requires authentication)."""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    now = datetime.now(timezone.utc)
    if reference_date:
        try:
            ref = datetime.fromisoformat(reference_date).replace(tzinfo=timezone.utc)
        except ValueError:
            ref = now
    else:
        ref = now

    if period == "week":
        # Monday of the week containing ref
        monday = ref - timedelta(days=ref.weekday())
        cutoff = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = cutoff + timedelta(days=7)
    elif period == "year":
        cutoff = ref.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = cutoff.replace(year=cutoff.year + 1)
    else:  # month
        cutoff = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if cutoff.month == 12:
            end = cutoff.replace(year=cutoff.year + 1, month=1)
        else:
            end = cutoff.replace(month=cutoff.month + 1)

    spenden = db.query(Spende).filter(Spende.date >= cutoff, Spende.date < end).all()
    spende_total = sum(s.amount for s in spenden)

    return {
        "spende_total": round(spende_total, 2),
        "spende_count": len(spenden),
        "period": period,
        "cutoff": cutoff.isoformat(),
        "end": end.isoformat(),
    }


class SpendeCreate(BaseModel):
    amount: float
    donor_name: Optional[str] = None
    date: Optional[str] = None
    notes: Optional[str] = None


@router.post("/api/buchhaltung/spende")
async def create_spende(
    data: SpendeCreate, request: Request, db: Session = Depends(get_db)
):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    date = (
        datetime.fromisoformat(data.date) if data.date else datetime.now(timezone.utc)
    )
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
async def delete_spende(
    spende_id: int, request: Request, db: Session = Depends(get_db)
):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    s = db.query(Spende).filter(Spende.id == spende_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Spende not found")
    db.delete(s)
    db.commit()
    return {"success": True}

"""Catalog routes - API and pages for material catalog"""

from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .models import Location, MaterialKategorie, MaterialVariante

router = APIRouter()


class LocationCreate(BaseModel):
    name: str


class LocationUpdate(BaseModel):
    name: Optional[str] = None


class KategorieCreate(BaseModel):
    location_id: int
    name: str
    pricing_model: str = "per_unit"
    unit: Optional[str] = None
    tax_rate: float = 19.0


class KategorieUpdate(BaseModel):
    name: Optional[str] = None
    pricing_model: Optional[str] = None
    unit: Optional[str] = None
    tax_rate: Optional[float] = None


class VarianteCreate(BaseModel):
    kategorie_id: int
    name: str
    price: float


class VarianteUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None


class BulkVarianteIn(BaseModel):
    name: str
    price: float


class BulkKategorieIn(BaseModel):
    name: str
    pricing_model: str = "per_unit"
    unit: Optional[str] = None
    tax_rate: float = 19.0
    varianten: list[BulkVarianteIn] = []


class BulkImportIn(BaseModel):
    location_name: str
    kategorien: list[BulkKategorieIn] = []


@router.on_event("startup")
async def startup():
    init_db()


# ── Page ─────────────────────────────────────────────────────────────────────


@router.get("/katalog", response_class=HTMLResponse)
async def katalog_page(request: Request):
    """Render Katalog management page"""
    from fastapi.templating import Jinja2Templates
    from backend.auth.dependencies import check_auth

    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("katalog.html", {"request": request})


# ── Full Catalog API ─────────────────────────────────────────────────────────


@router.get("/api/katalog")
async def get_full_katalog(db: Session = Depends(get_db)):
    """Return full catalog tree: locations with their categories and variants"""
    locations = db.query(Location).order_by(Location.name).all()
    result = []
    for loc in locations:
        loc_dict = loc.to_dict()
        kategorien = (
            db.query(MaterialKategorie)
            .filter(MaterialKategorie.location_id == loc.id)
            .order_by(MaterialKategorie.name)
            .all()
        )
        loc_dict["kategorien"] = []
        for kat in kategorien:
            kat_dict = kat.to_dict()
            varianten = (
                db.query(MaterialVariante)
                .filter(MaterialVariante.kategorie_id == kat.id)
                .order_by(MaterialVariante.name)
                .all()
            )
            kat_dict["varianten"] = [v.to_dict() for v in varianten]
            loc_dict["kategorien"].append(kat_dict)
        result.append(loc_dict)
    return result


# ── Locations API ─────────────────────────────────────────────────────────────


@router.get("/api/katalog/locations")
async def list_locations(db: Session = Depends(get_db)):
    """List all locations (storage areas)"""
    return [loc.to_dict() for loc in db.query(Location).order_by(Location.name).all()]


@router.post("/api/katalog/locations")
async def create_location(data: LocationCreate, db: Session = Depends(get_db)):
    """Create a new location"""
    existing = db.query(Location).filter(Location.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=400, detail=f"Location '{data.name}' already exists"
        )
    loc = Location(name=data.name)
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc.to_dict()


@router.put("/api/katalog/locations/{loc_id}")
async def update_location(
    loc_id: int, data: LocationUpdate, db: Session = Depends(get_db)
):
    """Update a location"""
    loc = db.query(Location).filter(Location.id == loc_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    if data.name is not None:
        loc.name = data.name
    db.commit()
    db.refresh(loc)
    return loc.to_dict()


@router.delete("/api/katalog/locations/{loc_id}")
async def delete_location(loc_id: int, db: Session = Depends(get_db)):
    """Delete a location"""
    loc = db.query(Location).filter(Location.id == loc_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    db.delete(loc)
    db.commit()
    return {"success": True}


# ── Kategorien API ────────────────────────────────────────────────────────────


@router.get("/api/katalog/kategorien")
async def list_kategorien(
    location_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """List all material categories"""
    q = db.query(MaterialKategorie)
    if location_id:
        q = q.filter(MaterialKategorie.location_id == location_id)
    return [k.to_dict() for k in q.order_by(MaterialKategorie.name).all()]


@router.post("/api/katalog/kategorien")
async def create_kategorie(data: KategorieCreate, db: Session = Depends(get_db)):
    """Create a new material category"""
    k = MaterialKategorie(
        location_id=data.location_id,
        name=data.name,
        pricing_model=data.pricing_model,
        unit=data.unit,
        tax_rate=data.tax_rate,
    )
    db.add(k)
    db.commit()
    db.refresh(k)
    return k.to_dict()


@router.put("/api/katalog/kategorien/{kat_id}")
async def update_kategorie(
    kat_id: int, data: KategorieUpdate, db: Session = Depends(get_db)
):
    """Update a material category"""
    k = db.query(MaterialKategorie).filter(MaterialKategorie.id == kat_id).first()
    if not k:
        raise HTTPException(status_code=404, detail="Kategorie not found")
    if data.name is not None:
        k.name = data.name
    if data.pricing_model is not None:
        k.pricing_model = data.pricing_model
    if data.unit is not None:
        k.unit = data.unit
    if data.tax_rate is not None:
        k.tax_rate = data.tax_rate
    db.commit()
    db.refresh(k)
    return k.to_dict()


@router.delete("/api/katalog/kategorien/{kat_id}")
async def delete_kategorie(kat_id: int, db: Session = Depends(get_db)):
    """Delete a material category"""
    k = db.query(MaterialKategorie).filter(MaterialKategorie.id == kat_id).first()
    if not k:
        raise HTTPException(status_code=404, detail="Kategorie not found")
    db.delete(k)
    db.commit()
    return {"success": True}


# ── Varianten API ─────────────────────────────────────────────────────────────


@router.get("/api/katalog/varianten")
async def list_varianten(
    kategorie_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """List all material variants"""
    q = db.query(MaterialVariante)
    if kategorie_id:
        q = q.filter(MaterialVariante.kategorie_id == kategorie_id)
    return [v.to_dict() for v in q.order_by(MaterialVariante.name).all()]


@router.post("/api/katalog/varianten")
async def create_variante(data: VarianteCreate, db: Session = Depends(get_db)):
    """Create a new material variant"""
    v = MaterialVariante(
        kategorie_id=data.kategorie_id,
        name=data.name,
        price=data.price,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v.to_dict()


@router.put("/api/katalog/varianten/{var_id}")
async def update_variante(
    var_id: int, data: VarianteUpdate, db: Session = Depends(get_db)
):
    """Update a material variant"""
    v = db.query(MaterialVariante).filter(MaterialVariante.id == var_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Variante not found")
    if data.name is not None:
        v.name = data.name
    if data.price is not None:
        v.price = data.price
    db.commit()
    db.refresh(v)
    return v.to_dict()


@router.delete("/api/katalog/varianten/{var_id}")
async def delete_variante(var_id: int, db: Session = Depends(get_db)):
    """Delete a material variant"""
    v = db.query(MaterialVariante).filter(MaterialVariante.id == var_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Variante not found")
    db.delete(v)
    db.commit()
    return {"success": True}


# ── Bulk Import ───────────────────────────────────────────────────────────────

_VALID_PRICING_MODELS = {
    "per_unit", "per_gram", "per_volume_cm3", "per_volume_l", "per_minute"
}
_VALID_TAX_RATES = {0, 7, 19, 0.0, 7.0, 19.0}


@router.post("/api/katalog/bulk-import")
async def bulk_import(data: BulkImportIn, db: Session = Depends(get_db)):
    """Find-or-create a location then bulk-create all categories and variants in
    one atomic transaction. Returns a summary of what was created."""
    for kat in data.kategorien:
        if kat.pricing_model not in _VALID_PRICING_MODELS:
            raise HTTPException(
                status_code=400,
                detail=f"Ungültiges Preismodell: '{kat.pricing_model}'",
            )
        if kat.tax_rate not in _VALID_TAX_RATES:
            raise HTTPException(
                status_code=400,
                detail=f"Ungültiger Steuersatz: {kat.tax_rate}. Erlaubt: 0, 7, 19",
            )

    loc = db.query(Location).filter(Location.name == data.location_name).first()
    if not loc:
        loc = Location(name=data.location_name)
        db.add(loc)
        db.flush()

    created_kategorien = 0
    created_varianten = 0
    try:
        for kat_data in data.kategorien:
            kat = MaterialKategorie(
                location_id=loc.id,
                name=kat_data.name,
                pricing_model=kat_data.pricing_model,
                unit=kat_data.unit,
                tax_rate=kat_data.tax_rate,
            )
            db.add(kat)
            db.flush()
            created_kategorien += 1
            for var_data in kat_data.varianten:
                db.add(
                    MaterialVariante(
                        kategorie_id=kat.id,
                        name=var_data.name,
                        price=var_data.price,
                    )
                )
                created_varianten += 1
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Fehler beim Speichern: {str(e)}"
        )

    return {
        "success": True,
        "location": loc.to_dict(),
        "created_kategorien": created_kategorien,
        "created_varianten": created_varianten,
    }

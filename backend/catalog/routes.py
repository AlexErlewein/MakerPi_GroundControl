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


class KategorieUpdate(BaseModel):
    name: Optional[str] = None
    pricing_model: Optional[str] = None
    unit: Optional[str] = None


class VarianteCreate(BaseModel):
    kategorie_id: int
    name: str
    price: float


class VarianteUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None


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
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("katalog.html", {"request": request})


# ── Full Catalog API ─────────────────────────────────────────────────────────

@router.get("/api/katalog")
async def get_full_katalog(db: Session = Depends(get_db)):
    """Return full catalog tree: locations with their categories and variants"""
    locations = db.query(Location).order_by(Location.name).all()
    result = []
    for loc in locations:
        loc_dict = loc.to_dict()
        kategorien = db.query(MaterialKategorie).filter(
            MaterialKategorie.location_id == loc.id
        ).order_by(MaterialKategorie.name).all()
        loc_dict["kategorien"] = []
        for kat in kategorien:
            kat_dict = kat.to_dict()
            varianten = db.query(MaterialVariante).filter(
                MaterialVariante.kategorie_id == kat.id
            ).order_by(MaterialVariante.name).all()
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
        raise HTTPException(status_code=400, detail=f"Location '{data.name}' already exists")
    loc = Location(name=data.name)
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc.to_dict()


@router.put("/api/katalog/locations/{loc_id}")
async def update_location(loc_id: int, data: LocationUpdate, db: Session = Depends(get_db)):
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
async def list_kategorien(location_id: Optional[int] = None, db: Session = Depends(get_db)):
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
    )
    db.add(k)
    db.commit()
    db.refresh(k)
    return k.to_dict()


@router.put("/api/katalog/kategorien/{kat_id}")
async def update_kategorie(kat_id: int, data: KategorieUpdate, db: Session = Depends(get_db)):
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
async def list_varianten(kategorie_id: Optional[int] = None, db: Session = Depends(get_db)):
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
async def update_variante(var_id: int, data: VarianteUpdate, db: Session = Depends(get_db)):
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

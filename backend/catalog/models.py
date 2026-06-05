"""Catalog models - material catalog structure"""

from sqlalchemy import Boolean, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class MaterialKategorie(Base):
    __tablename__ = "material_kategorie"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, index=True)
    name = Column(String)
    pricing_model = Column(
        String, default="per_unit"
    )  # vestigial – pricing is now on MaterialUnterkategorie
    unit = Column(String, nullable=True)  # vestigial
    tax_rate = Column(Float, default=19.0)  # vestigial

    def to_dict(self):
        return {
            "id": self.id,
            "location_id": self.location_id,
            "name": self.name,
            "pricing_model": self.pricing_model,
            "unit": self.unit,
            "tax_rate": self.tax_rate if self.tax_rate is not None else 19.0,
        }


class MaterialUnterkategorie(Base):
    __tablename__ = "material_unterkategorie"

    id = Column(Integer, primary_key=True, index=True)
    kategorie_id = Column(Integer, index=True)
    name = Column(String)
    tax_rate = Column(Float, default=19.0)  # 0 | 7 | 19
    is_spende = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "kategorie_id": self.kategorie_id,
            "name": self.name,
            "tax_rate": self.tax_rate if self.tax_rate is not None else 19.0,
            "is_spende": bool(self.is_spende) if self.is_spende is not None else False,
        }


class MaterialVariante(Base):
    __tablename__ = "material_variante"

    id = Column(Integer, primary_key=True, index=True)
    kategorie_id = Column(Integer, index=True)  # kept for backward compat
    unterkategorie_id = Column(Integer, index=True, nullable=True)
    name = Column(String)
    price = Column(Float)  # price per unit
    pricing_model = Column(String, default="per_unit")  # per_unit | per_gram | per_kilogram | per_volume_cm3 | per_volume_l | per_minute etc.
    unit = Column(String, nullable=True)  # display unit
    tax_rate = Column(Float, default=19.0)  # 0 | 7 | 19
    is_spende = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "kategorie_id": self.kategorie_id,
            "unterkategorie_id": self.unterkategorie_id,
            "name": self.name,
            "price": self.price,
            "pricing_model": self.pricing_model if self.pricing_model else "per_unit",
            "unit": self.unit,
            "tax_rate": self.tax_rate if self.tax_rate is not None else 19.0,
            "is_spende": bool(self.is_spende) if self.is_spende is not None else False,
        }

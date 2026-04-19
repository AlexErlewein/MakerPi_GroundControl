"""Catalog models - material catalog structure"""

from sqlalchemy import Column, Integer, String, Float
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
    pricing_model = Column(String, default="per_unit")  # per_gram | per_volume_cm3 | per_volume_l | per_minute | per_unit
    unit = Column(String, nullable=True)  # display unit

    def to_dict(self):
        return {
            "id": self.id,
            "location_id": self.location_id,
            "name": self.name,
            "pricing_model": self.pricing_model,
            "unit": self.unit,
        }


class MaterialVariante(Base):
    __tablename__ = "material_variante"

    id = Column(Integer, primary_key=True, index=True)
    kategorie_id = Column(Integer, index=True)
    name = Column(String)
    price = Column(Float)  # price per unit

    def to_dict(self):
        return {
            "id": self.id,
            "kategorie_id": self.kategorie_id,
            "name": self.name,
            "price": self.price,
        }

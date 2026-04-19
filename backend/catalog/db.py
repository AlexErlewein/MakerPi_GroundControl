"""Catalog database - owns catalog.db"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.config import CATALOG_DB_URL
from .models import Base

engine = create_engine(CATALOG_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)

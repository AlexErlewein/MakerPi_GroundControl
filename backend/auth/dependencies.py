"""Auth dependencies for FastAPI"""

from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from .db import SessionLocal
from .models import User
from backend.config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def check_auth(request: Request) -> bool:
    """Check if user is authenticated"""
    return request.session.get("user") is not None


def get_current_user(request: Request) -> str | None:
    """Get current username from session"""
    return request.session.get("user")


def get_user(db: Session, username: str) -> User | None:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def seed_admin_user():
    """Seed default admin user if no users exist"""
    db = SessionLocal()
    try:
        existing = db.query(User).first()
        if existing:
            return
        hashed = get_password_hash(ADMIN_PASSWORD)
        admin = User(
            username=ADMIN_USERNAME,
            hashed_password=hashed,
            role="admin"
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()

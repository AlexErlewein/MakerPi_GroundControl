"""Auth dependencies for FastAPI"""

from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from .db import SessionLocal
from .models import User
from backend.config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ADMIN_TIMEOUT_MINUTES = 10
MEMBER_TIMEOUT_MINUTES = 3


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


def is_admin_verified(request: Request) -> bool:
    """Check if user has verified admin status (with 10min timeout)"""
    session = request.session
    if not session.get("admin_verified"):
        return False
    
    admin_verified_at = session.get("admin_verified_at")
    last_activity = session.get("last_activity")
    
    if not admin_verified_at or not last_activity:
        return False
    
    # Parse ISO format strings to datetime
    try:
        last_activity_dt = datetime.fromisoformat(last_activity)
        if last_activity_dt.tzinfo is None:
            last_activity_dt = last_activity_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return False
    
    # Check 10min timeout
    now = datetime.now(timezone.utc)
    if (now - last_activity_dt).total_seconds() > (ADMIN_TIMEOUT_MINUTES * 60):
        # Timeout expired, clear admin verification
        session["admin_verified"] = False
        session["admin_verified_at"] = None
        return False
    
    # Update last activity
    session["last_activity"] = now.isoformat()
    return True


def is_member_session_valid(request: Request) -> bool:
    """Check if member session is still valid (3min timeout)"""
    session = request.session
    if not session.get("user"):
        return False
    
    last_activity = session.get("last_activity")
    
    if not last_activity:
        return False
    
    # Parse ISO format string to datetime
    try:
        last_activity_dt = datetime.fromisoformat(last_activity)
        if last_activity_dt.tzinfo is None:
            last_activity_dt = last_activity_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return False
    
    # Check 3min timeout
    now = datetime.now(timezone.utc)
    if (now - last_activity_dt).total_seconds() > (MEMBER_TIMEOUT_MINUTES * 60):
        # Timeout expired, clear session
        session.clear()
        return False
    
    # Update last activity
    session["last_activity"] = now.isoformat()
    return True


def verify_admin_password(request: Request, db: Session, password: str) -> bool:
    """Verify admin password and enable admin mode"""
    if not request.session.get("user"):
        return False
    
    # Check if user is admin-capable
    is_admin_capable = request.session.get("is_admin_capable", False)
    if not is_admin_capable:
        return False
    
    # Get user and verify password
    username = request.session.get("user")
    user = db.query(User).filter(User.username == username).first()
    
    if not user or user.role != "admin":
        return False
    
    if not verify_password(password, user.hashed_password):
        return False
    
    # Set admin verified
    now = datetime.now(timezone.utc)
    request.session["admin_verified"] = True
    request.session["admin_verified_at"] = now.isoformat()
    request.session["last_activity"] = now.isoformat()
    return True


def get_session_info(request: Request) -> dict:
    """Get current session information"""
    session = request.session
    return {
        "mitglied_id": session.get("mitglied_id"),
        "is_admin_capable": session.get("is_admin_capable", False),
        "admin_verified": is_admin_verified(request),
        "can_access_admin": is_admin_verified(request),
    }


def require_auth(request: Request):
    """Dependency: require authentication"""
    if not request.session.get("user"):
        raise HTTPException(status_code=401, detail="Not authenticated")


def require_admin(request: Request):
    """Dependency: require admin verification"""
    if not is_admin_verified(request):
        raise HTTPException(status_code=403, detail="Admin verification required")


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
            role="admin",
            mitglied_id=None
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()

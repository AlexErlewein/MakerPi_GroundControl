"""Auth models - User table"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def _utcnow():
    """Get current UTC time as timezone-aware datetime"""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

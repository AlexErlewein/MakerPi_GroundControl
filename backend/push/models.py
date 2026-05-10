"""Push notification subscription models."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(512), unique=True, nullable=False, index=True)
    p256dh = Column(String(256), nullable=False)
    auth = Column(String(128), nullable=False)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "endpoint": self.endpoint,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

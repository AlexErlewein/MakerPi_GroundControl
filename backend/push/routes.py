"""Push notification API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pywebpush import webpush, WebPushException
from pydantic import BaseModel
import json
import os

from .db import get_db, init_db
from .models import PushSubscription

router = APIRouter()

# VAPID keys — generated on first use if not set
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS = {"sub": "mailto:makerspace@h3cke.de"}


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict = {}


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


@router.on_event("startup")
def startup():
    init_db()
    _ensure_vapid_keys()


def _ensure_vapid_keys():
    """Generate VAPID keys if not configured."""
    global VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY
    if VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY:
        return

    try:
        from py_vapid import Vapid
        import os as _os

        # Check for persisted keys
        key_dir = _os.environ.get("VAPID_KEY_DIR", "config")
        priv_path = _os.path.join(key_dir, "vapid_private.pem")
        pub_path = _os.path.join(key_dir, "vapid_public.pem")

        if _os.path.exists(priv_path):
            with open(priv_path, "r") as f:
                VAPID_PRIVATE_KEY = f.read().strip()
            if _os.path.exists(pub_path):
                with open(pub_path, "r") as f:
                    VAPID_PUBLIC_KEY = f.read().strip()
        else:
            # Generate new keys
            _os.makedirs(key_dir, exist_ok=True)
            v = Vapid()
            v.generate_keys()
            v.save_key(priv_path)
            v.save_public_key(pub_path)
            with open(priv_path, "r") as f:
                VAPID_PRIVATE_KEY = f.read().strip()
            with open(pub_path, "r") as f:
                VAPID_PUBLIC_KEY = f.read().strip()
    except Exception as e:
        print(f"[Push] Warning: Could not generate VAPID keys: {e}")
        print(
            "[Push] Push notifications will be unavailable until VAPID keys are configured."
        )


@router.get("/api/push/vapid-key")
def get_vapid_key():
    """Return the public VAPID key for client-side subscription."""
    return {"publicKey": VAPID_PUBLIC_KEY}


@router.post("/api/push/subscribe")
def subscribe(sub: PushSubscriptionRequest, db: Session = Depends(get_db)):
    """Store a push subscription from the client."""
    endpoint = sub.endpoint
    keys = sub.keys

    if not endpoint:
        return {"success": False, "error": "Missing endpoint"}

    # Upsert subscription
    existing = (
        db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    )

    if existing:
        existing.p256dh = keys.get("p256dh", existing.p256dh)
        existing.auth = keys.get("auth", existing.auth)
    else:
        sub_obj = PushSubscription(
            endpoint=endpoint,
            p256dh=keys.get("p256dh", ""),
            auth=keys.get("auth", ""),
        )
        db.add(sub_obj)

    db.commit()
    return {"success": True}


@router.post("/api/push/unsubscribe")
def unsubscribe(unsub: PushUnsubscribeRequest, db: Session = Depends(get_db)):
    """Remove a push subscription."""
    endpoint = unsub.endpoint
    if endpoint:
        sub = (
            db.query(PushSubscription)
            .filter(PushSubscription.endpoint == endpoint)
            .first()
        )
        if sub:
            db.delete(sub)
            db.commit()
    return {"success": True}


def send_push_notification(
    title: str,
    body: str,
    tag: str = "gc-notification",
    url: str = "/dashboard",
    actions: list = None,
):
    """Send a push notification to ALL subscribed devices."""
    if not VAPID_PRIVATE_KEY:
        return 0

    from .db import SessionLocal

    db = SessionLocal()
    sent = 0

    try:
        subscriptions = db.query(PushSubscription).all()
        payload = json.dumps(
            {
                "title": title,
                "body": body,
                "tag": tag,
                "data": {"url": url},
                "actions": actions or [],
            }
        )

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                    },
                    data=payload,
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims=VAPID_CLAIMS,
                )
                sent += 1
            except WebPushException as e:
                # Remove expired subscriptions
                if "410" in str(e) or "expired" in str(e).lower():
                    db.delete(sub)
            except Exception:
                pass

        db.commit()
    finally:
        db.close()

    return sent

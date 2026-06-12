"""OAuth authentication routes for Google OAuth 2.0"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from backend.auth.db import SessionLocal
from backend.auth.models import User
from backend.config import (
    OAUTH_ENABLED,
    OAUTH_GOOGLE_CLIENT_ID,
    OAUTH_GOOGLE_CLIENT_SECRET,
    OAUTH_GOOGLE_REDIRECT_URI,
)

router = APIRouter()

# Lazy import OAuth to avoid import errors if authlib is not installed
_oauth_instance = None


def get_oauth():
    """Initialize OAuth instance lazily"""
    global _oauth_instance
    if _oauth_instance is None:
        try:
            from authlib.integrations.fastapi_oauthclient import OAuth

            _oauth_instance = OAuth()
            _oauth_instance.register(
                "google",
                client_id=OAUTH_GOOGLE_CLIENT_ID,
                client_secret=OAUTH_GOOGLE_CLIENT_SECRET,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="OAuth dependencies not installed. Run: uv sync",
            )
    return _oauth_instance


@router.get("/auth/google")
async def login_google(request: Request):
    """Redirect to Google OAuth login"""
    if not OAUTH_ENABLED:
        raise HTTPException(status_code=403, detail="OAuth is not enabled")

    oauth = get_oauth()
    return await oauth.google.authorize_redirect(request, OAUTH_GOOGLE_REDIRECT_URI)


@router.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    """Handle Google OAuth callback"""
    if not OAUTH_ENABLED:
        raise HTTPException(status_code=403, detail="OAuth is not enabled")

    oauth = get_oauth()

    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)
        user_info = await oauth.google.parse_id_token(request, token)

        # Extract user information
        email = user_info.get("email")

        if not email:
            raise HTTPException(
                status_code=400, detail="Email not provided by OAuth provider"
            )

        # Get or create user in auth.db
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == email).first()

            if user:
                # User exists - update session
                # Check if user has admin role
                is_admin = user.role == "admin"
            else:
                # Create new user
                user = User(
                    username=email,
                    hashed_password="",  # No password for OAuth users
                    role="member",
                    mitglied_id=None,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                is_admin = False

            # Create session
            request.session["user"] = email
            request.session["mitglied_id"] = user.mitglied_id
            request.session["is_admin_capable"] = is_admin
            request.session["login_method"] = "oauth"
            request.session["admin_verified"] = is_admin  # Auto-verify for OAuth users
            request.session["admin_verified_at"] = (
                datetime.now(timezone.utc).isoformat() if is_admin else None
            )
            request.session["last_activity"] = datetime.now(timezone.utc).isoformat()

            # Redirect based on user type
            if is_admin and not user.mitglied_id:
                return RedirectResponse("/dashboard", status_code=302)
            else:
                return RedirectResponse("/member", status_code=302)

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"OAuth callback failed: {str(e)}"
            )
        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"OAuth authentication failed: {str(e)}"
        )


@router.get("/auth/oauth/status")
async def oauth_status():
    """Check if OAuth is enabled and configured"""
    return {
        "enabled": OAUTH_ENABLED,
        "google_configured": bool(
            OAUTH_GOOGLE_CLIENT_ID and OAUTH_GOOGLE_CLIENT_SECRET
        ),
        "redirect_uri": OAUTH_GOOGLE_REDIRECT_URI if OAUTH_ENABLED else None,
    }

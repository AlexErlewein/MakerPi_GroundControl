"""Auth routes - login, logout, admin users"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.config import ADMIN_USERNAME

from .db import get_db, init_db
from .dependencies import (
    get_password_hash,
    get_session_info,
    get_user,
    is_admin_verified,
    is_member_session_valid,
    seed_admin_user,
    verify_admin_password,
    verify_password,
)
from .models import User
from .oauth import router as oauth_router

router = APIRouter()

# Include OAuth router
router.include_router(oauth_router)


@router.on_event("startup")
async def startup():
    init_db()
    seed_admin_user()


@router.get("/")
async def landing_page(request: Request):
    """Landing page - redirects to member view if logged in"""
    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")

    if request.session.get("user"):
        return RedirectResponse("/member", status_code=302)
    return templates.TemplateResponse("landing.html", {"request": request})


@router.get("/login")
async def login_page(request: Request, error: str = None):
    """Redirect to modern landing page (old login.html deprecated)"""
    if request.session.get("user"):
        return RedirectResponse("/member", status_code=302)
    url = "/"
    if error:
        url += f"?error={error}"
    return RedirectResponse(url, status_code=302)


@router.post("/api/auth/login")
async def unified_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Unified login - admins go to dashboard, members to /member"""
    from backend.members.db import get_db as get_members_db
    from backend.members.models import Mitglied

    members_db = next(get_members_db())

    # Check admin users first
    user = get_user(db, username)
    if (
        user
        and user.hashed_password
        and verify_password(password, user.hashed_password)
    ):
        request.session["user"] = user.username
        request.session["mitglied_id"] = user.mitglied_id
        request.session["is_admin_capable"] = user.role == "admin"
        request.session["login_method"] = "password"
        request.session["admin_verified"] = False
        request.session["admin_verified_at"] = None
        request.session["last_activity"] = datetime.now(timezone.utc).isoformat()

        if user.role == "admin" and not user.mitglied_id:
            # Admin-only user — auto-verify (password just entered), go to dashboard
            request.session["admin_verified"] = True
            request.session["admin_verified_at"] = datetime.now(
                timezone.utc
            ).isoformat()
            return RedirectResponse("/dashboard", status_code=302)
        else:
            # Member (or hybrid member+admin) — land on member view
            return RedirectResponse("/member", status_code=302)

    # Check member login via mitglieder table
    try:
        mitglied = (
            members_db.query(Mitglied)
            .filter(Mitglied.login_username == username)
            .first()
        )
        if mitglied and mitglied.login_password_hash:
            if verify_password(password, mitglied.login_password_hash):
                # Ensure user record exists in auth db, keyed by login_username
                member_user = (
                    db.query(User)
                    .filter(User.username == mitglied.login_username)
                    .first()
                )
                if not member_user:
                    # Also check by mitglied_id in case of RFID-created user
                    member_user = (
                        db.query(User).filter(User.mitglied_id == mitglied.id).first()
                    )
                if not member_user:
                    member_user = User(
                        username=mitglied.login_username,
                        hashed_password="",  # Not used - auth via mitglieder table
                        role="member",
                        mitglied_id=mitglied.id,
                    )
                    db.add(member_user)
                    db.commit()
                elif member_user.username != mitglied.login_username:
                    # Update username to match current login_username
                    member_user.username = mitglied.login_username
                    db.commit()

                # Check if member has admin RFID tag
                from backend.members.models import RFIDTag

                admin_tag = (
                    members_db.query(RFIDTag)
                    .filter(
                        RFIDTag.member_id == mitglied.member_id,
                        RFIDTag.is_admin.is_(True),
                        RFIDTag.active == 1,
                    )
                    .first()
                )
                has_admin = bool(admin_tag) or (
                    member_user and member_user.role == "admin"
                )

                request.session["user"] = mitglied.login_username
                request.session["mitglied_id"] = mitglied.id
                request.session["is_admin_capable"] = has_admin
                request.session["login_method"] = "password"
                request.session["admin_verified"] = False
                request.session["admin_verified_at"] = None
                request.session["last_activity"] = datetime.now(
                    timezone.utc
                ).isoformat()
                return RedirectResponse("/member", status_code=302)
    finally:
        members_db.close()

    return RedirectResponse("/?error=Invalid+credentials", status_code=302)


@router.post("/login")  # Keep for form compatibility
async def legacy_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Legacy login endpoint - redirects to unified login"""
    return await unified_login(request, username, password, db)


@router.get("/logout")
async def logout(request: Request):
    """Clear session"""
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@router.post("/api/auth/logout-admin")
async def logout_admin(request: Request):
    """Drop admin verification, return to member view"""
    request.session["admin_verified"] = False
    request.session["admin_verified_at"] = None
    return RedirectResponse("/member", status_code=302)


@router.get("/api/auth/session")
async def session_info(request: Request):
    """Get current session information"""
    return get_session_info(request)


@router.post("/api/auth/heartbeat")
async def heartbeat(request: Request):
    """Update last activity timestamp and check session validity"""
    if not is_member_session_valid(request):
        return JSONResponse({"valid": False}, status_code=401)
    return {"valid": True}


@router.post("/api/auth/verify-admin")
async def verify_admin(
    request: Request, password: str = Form(...), db: Session = Depends(get_db)
):
    """Verify admin password to enable admin mode"""
    if verify_admin_password(request, db, password):
        return {"success": True}
    return JSONResponse(
        {"success": False, "error": "Invalid password or not admin"}, status_code=403
    )


@router.post("/api/auth/verify-admin-auto")
async def verify_admin_auto(request: Request):
    """Auto-verify admin mode without password (only if login_method is 'password')."""
    if not request.session.get("is_admin_capable"):
        return JSONResponse(
            {"success": False, "error": "Not admin capable"}, status_code=403
        )
    if request.session.get("login_method") != "password":
        return JSONResponse(
            {"success": False, "error": "requires_password"}, status_code=403
        )
    now = datetime.now(timezone.utc)
    request.session["admin_verified"] = True
    request.session["admin_verified_at"] = now.isoformat()
    request.session["last_activity"] = now.isoformat()
    return {"success": True}


@router.get("/admin/users")
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    """User management page - requires admin verification"""
    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")

    if not request.session.get("user"):
        return RedirectResponse("/", status_code=302)

    # Require admin verification
    if not is_admin_verified(request):
        return RedirectResponse("/member?admin_required=1", status_code=302)

    users = db.query(User).order_by(User.created_at).all()

    from backend.members.db import SessionLocal as MembersSession
    from backend.members.models import Mitglied

    members_db = MembersSession()
    try:
        members_with_login = (
            members_db.query(Mitglied)
            .filter(Mitglied.login_username.isnot(None))
            .order_by(Mitglied.name)
            .all()
        )
    finally:
        members_db.close()

    return templates.TemplateResponse(
        "admin-users.html",
        {
            "request": request,
            "users": users,
            "members_with_login": members_with_login,
            "current_user": request.session.get("user"),
            "admin_username": ADMIN_USERNAME,
            "nav_active": "users",
            "success": None,
            "error": None,
        },
    )


@router.post("/admin/users/add")
async def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(default="member"),
    db: Session = Depends(get_db),
):
    """Add a new user"""
    if not request.session.get("user"):
        return RedirectResponse("/", status_code=302)

    if not is_admin_verified(request):
        return RedirectResponse("/member?admin_required=1", status_code=302)

    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")

    existing = get_user(db, username)
    if existing:
        users = db.query(User).order_by(User.created_at).all()
        return templates.TemplateResponse(
            "admin-users.html",
            {
                "request": request,
                "users": users,
                "current_user": request.session.get("user"),
                "nav_active": "users",
                "success": None,
                "error": f"User '{username}' already exists",
            },
            status_code=400,
        )

    hashed = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed, role=role)
    db.add(new_user)
    db.commit()

    users = db.query(User).order_by(User.created_at).all()
    return templates.TemplateResponse(
        "admin-users.html",
        {
            "request": request,
            "users": users,
            "current_user": request.session.get("user"),
            "nav_active": "users",
            "success": f"User '{username}' created",
            "error": None,
        },
    )


@router.post("/admin/users/toggle-role")
async def toggle_user_role(
    request: Request,
    user_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Toggle user role between admin and member"""
    if not request.session.get("user"):
        return RedirectResponse("/", status_code=302)

    if not is_admin_verified(request):
        return RedirectResponse("/member?admin_required=1", status_code=302)

    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")

    current_user = request.session.get("user")
    target = db.query(User).filter(User.id == user_id).first()

    if not target:
        users = db.query(User).order_by(User.created_at).all()
        return templates.TemplateResponse(
            "admin-users.html",
            {
                "request": request,
                "users": users,
                "current_user": current_user,
                "nav_active": "users",
                "success": None,
                "error": "User not found",
            },
            status_code=404,
        )

    if target.username == current_user:
        users = db.query(User).order_by(User.created_at).all()
        return templates.TemplateResponse(
            "admin-users.html",
            {
                "request": request,
                "users": users,
                "current_user": current_user,
                "nav_active": "users",
                "success": None,
                "error": "Cannot change your own role",
            },
            status_code=400,
        )

    # Toggle role
    new_role = "member" if target.role == "admin" else "admin"
    target.role = new_role
    db.commit()

    users = db.query(User).order_by(User.created_at).all()
    return templates.TemplateResponse(
        "admin-users.html",
        {
            "request": request,
            "users": users,
            "current_user": current_user,
            "nav_active": "users",
            "success": f"User '{target.username}' is now {new_role}",
            "error": None,
        },
    )


@router.post("/admin/users/delete")
async def delete_user(
    request: Request,
    user_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Delete a user (cannot delete self or last user)"""
    if not request.session.get("user"):
        return RedirectResponse("/", status_code=302)

    if not is_admin_verified(request):
        return RedirectResponse("/member?admin_required=1", status_code=302)

    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")

    current_user = request.session.get("user")
    target = db.query(User).filter(User.id == user_id).first()

    if not target:
        users = db.query(User).order_by(User.created_at).all()
        return templates.TemplateResponse(
            "admin-users.html",
            {
                "request": request,
                "users": users,
                "current_user": current_user,
                "nav_active": "users",
                "success": None,
                "error": "User not found",
            },
            status_code=404,
        )

    if target.username == current_user:
        users = db.query(User).order_by(User.created_at).all()
        return templates.TemplateResponse(
            "admin-users.html",
            {
                "request": request,
                "users": users,
                "current_user": current_user,
                "admin_username": ADMIN_USERNAME,
                "nav_active": "users",
                "success": None,
                "error": "Cannot delete yourself",
            },
            status_code=400,
        )

    if target.username == ADMIN_USERNAME:
        users = db.query(User).order_by(User.created_at).all()
        return templates.TemplateResponse(
            "admin-users.html",
            {
                "request": request,
                "users": users,
                "current_user": current_user,
                "admin_username": ADMIN_USERNAME,
                "nav_active": "users",
                "success": None,
                "error": f"Cannot delete the primary admin user '{ADMIN_USERNAME}'",
            },
            status_code=400,
        )

    total = db.query(User).count()
    if total <= 1:
        users = db.query(User).order_by(User.created_at).all()
        return templates.TemplateResponse(
            "admin-users.html",
            {
                "request": request,
                "users": users,
                "current_user": current_user,
                "nav_active": "users",
                "success": None,
                "error": "Cannot delete the last user",
            },
            status_code=400,
        )

    db.delete(target)
    db.commit()

    users = db.query(User).order_by(User.created_at).all()
    return templates.TemplateResponse(
        "admin-users.html",
        {
            "request": request,
            "users": users,
            "current_user": current_user,
            "nav_active": "users",
            "success": f"User '{target.username}' deleted",
            "error": None,
        },
    )


@router.post("/admin/users/promote-member-to-admin")
async def promote_member_to_admin(
    request: Request,
    mitglied_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Create an admin User in auth.db from a member's login credentials."""
    if not is_admin_verified(request):
        return RedirectResponse("/member?admin_required=1", status_code=302)

    from backend.members.db import SessionLocal as MembersSession
    from backend.members.models import Mitglied

    members_db = MembersSession()
    try:
        m = members_db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
        if not m or not m.login_username or not m.login_password_hash:
            return RedirectResponse("/admin/users", status_code=303)
        username = m.login_username
        password_hash = m.login_password_hash
    finally:
        members_db.close()

    if not db.query(User).filter(User.username == username).first():
        db.add(
            User(
                username=username,
                hashed_password=password_hash,
                role="admin",
                mitglied_id=mitglied_id,
            )
        )
        db.commit()

    return RedirectResponse("/admin/users", status_code=303)


@router.post("/admin/users/revoke-member-login")
async def revoke_member_login(
    request: Request,
    mitglied_id: int = Form(...),
):
    """Remove login credentials from a member (members.db)."""

    from backend.members.db import SessionLocal as MembersSession
    from backend.members.models import Mitglied

    if not is_admin_verified(request):
        return RedirectResponse("/member?admin_required=1", status_code=302)

    members_db = MembersSession()
    try:
        m = members_db.query(Mitglied).filter(Mitglied.id == mitglied_id).first()
        if m:
            m.login_username = None
            m.login_password_hash = None
            members_db.commit()
    finally:
        members_db.close()

    return RedirectResponse("/admin/users", status_code=303)


@router.post("/admin/users/change-password")
async def change_admin_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Allow the logged-in admin to change their own password."""
    if not is_admin_verified(request):
        return RedirectResponse("/member?admin_required=1", status_code=302)

    username = request.session.get("user")
    user = get_user(db, username)
    if not user or not verify_password(current_password, user.hashed_password):
        return RedirectResponse("/admin/users?pw_error=1", status_code=303)

    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return RedirectResponse("/admin/users?pw_success=1", status_code=303)

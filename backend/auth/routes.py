"""Auth routes - login, logout, admin users"""

from datetime import datetime, timezone
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .models import User
from .dependencies import (
    verify_password,
    get_password_hash,
    get_user,
    seed_admin_user,
    is_admin_verified,
    verify_admin_password,
    get_session_info,
    is_member_session_valid,
)

router = APIRouter()


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
    """Show login page (redirects if already logged in)"""
    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")

    if request.session.get("user"):
        return RedirectResponse("/member", status_code=302)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": error}
    )


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
        # Admin user found - auto-verify since password was just entered
        request.session["user"] = user.username
        request.session["mitglied_id"] = user.mitglied_id
        request.session["is_admin_capable"] = user.role == "admin"

        if user.role == "admin":
            # Direct admin access - password already verified
            request.session["admin_verified"] = True
            request.session["admin_verified_at"] = datetime.now(
                timezone.utc
            ).isoformat()
            request.session["last_activity"] = datetime.now(timezone.utc).isoformat()
            return RedirectResponse("/dashboard", status_code=302)
        else:
            # Regular member user
            request.session["admin_verified"] = False
            request.session["admin_verified_at"] = None
            request.session["last_activity"] = datetime.now(timezone.utc).isoformat()
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
    return templates.TemplateResponse(
        "admin-users.html",
        {
            "request": request,
            "users": users,
            "current_user": request.session.get("user"),
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
                "nav_active": "users",
                "success": None,
                "error": "Cannot delete yourself",
            },
            status_code=400,
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
                "error": "Cannot delete yourself",
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

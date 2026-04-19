"""Auth routes - login, logout, admin users"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .db import get_db, init_db
from .models import User
from .dependencies import verify_password, get_password_hash, get_user, seed_admin_user
from backend.config import SECRET_KEY

router = APIRouter()


@router.on_event("startup")
async def startup():
    init_db()
    seed_admin_user()


@router.get("/login")
async def login_page(request: Request, error: str = None):
    """Show login page (redirects if already logged in)"""
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="templates")
    
    if request.session.get("user"):
        role = request.session.get("role")
        if role == "admin":
            return RedirectResponse("/dashboard", status_code=302)
        else:
            return RedirectResponse("/member", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Authenticate and set session"""
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse("/login?error=Invalid+credentials", status_code=302)
    request.session["user"] = user.username
    request.session["role"] = user.role
    request.session["mitglied_id"] = user.mitglied_id
    # Redirect based on role
    if user.role == "admin":
        return RedirectResponse("/dashboard", status_code=302)
    else:
        return RedirectResponse("/member", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    """Clear session"""
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@router.get("/admin/users")
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    """User management page"""
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="templates")
    
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    
    users = db.query(User).order_by(User.created_at).all()
    return templates.TemplateResponse(
        "admin-users.html",
        {
            "request": request,
            "users": users,
            "current_user": request.session.get("user"),
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
        return RedirectResponse("/login", status_code=302)
    
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
            "success": f"User '{username}' created",
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
        return RedirectResponse("/login", status_code=302)
    
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
            "success": f"User '{target.username}' deleted",
            "error": None,
        },
    )

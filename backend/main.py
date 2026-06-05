"""MakerPi GroundControl - Modular FastAPI Application
Mounts all domain modules as separate route collections
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from backend.config import SECRET_KEY
from backend.middleware import PWASessionMiddleware
from backend.auth.routes import router as auth_router
from backend.members.routes import router as members_router
from backend.laufzettel.routes import router as laufzettel_router
from backend.catalog.routes import router as catalog_router
from backend.buchhaltung.routes import router as buchhaltung_router
from backend.core.routes import router as core_router
from backend.member_routes import router as member_router
from backend.push.routes import router as push_router
from backend.shopify.routes import router as shopify_router
from backend.plane.routes import router as plane_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.members.easyverein import sync_members_from_easyverein, check_easyverein_key_expiry
from backend.laufzettel.db import SessionLocal as LaufzettelSession
from backend.laufzettel.models import Laufzettel, LaufzettelMaterial

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup
app = FastAPI(title="MakerPi GroundControl")

scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def start_scheduler():
    """Start the background scheduler"""
    # Schedule easyVerein sync daily at 03:00
    scheduler.add_job(
        sync_members_from_easyverein,
        CronTrigger(hour=3, minute=0),
        id="easyverein_daily_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        check_easyverein_key_expiry,
        CronTrigger(hour=9, minute=0),
        id="easyverein_key_expiry_check",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_empty_laufzettel,
        CronTrigger(hour=4, minute=0),
        id="cleanup_empty_laufzettel",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started with daily easyVerein sync at 03:00")


async def cleanup_empty_laufzettel():
    """Nightly job: delete open laufzettel from previous days that have no materials."""
    from datetime import date
    today = date.today()
    db = LaufzettelSession()
    try:
        stale_empty = (
            db.query(Laufzettel)
            .filter(
                Laufzettel.payment_method.is_(None),
                Laufzettel.date < today,
            )
            .all()
        )
        deleted = 0
        for lz in stale_empty:
            has_materials = (
                db.query(LaufzettelMaterial)
                .filter(LaufzettelMaterial.laufzettel_id == lz.id)
                .first()
            )
            if not has_materials:
                db.delete(lz)
                deleted += 1
        db.commit()
        logger.info("[cleanup_empty_laufzettel] Deleted %d empty stale laufzettel", deleted)
    except Exception:
        logger.exception("[cleanup_empty_laufzettel] Failed")
        db.rollback()
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_scheduler():
    """Shutdown the scheduler gracefully"""
    scheduler.shutdown()
    logger.info("APScheduler shutdown")


@app.on_event("shutdown")
async def checkpoint_all_wal():
    """Checkpoint all WAL files on graceful shutdown to prevent corruption on next open."""
    from backend.auth.db import engine as auth_engine
    from backend.core.db import engine as core_engine
    from backend.members.db import engine as members_engine
    from backend.laufzettel.db import engine as laufzettel_engine
    from backend.catalog.db import engine as catalog_engine
    from backend.buchhaltung.db import engine as buchhaltung_engine
    from backend.push.db import engine as push_engine

    engines = [auth_engine, core_engine, members_engine, laufzettel_engine, catalog_engine, buchhaltung_engine, push_engine]
    for eng in engines:
        try:
            with eng.connect() as conn:
                conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
        except Exception as e:
            logger.warning("WAL checkpoint failed for %s: %s", eng.url, e)
    logger.info("WAL checkpoint complete for all databases")


# Session middleware (required for auth)
# Uses PWASessionMiddleware to omit SameSite so iOS PWA fetch() calls send the cookie
app.add_middleware(PWASessionMiddleware, secret_key=SECRET_KEY)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/graphics", StaticFiles(directory="graphics"), name="graphics")

# Templates
templates = Jinja2Templates(directory="templates")

# Mount all module routers
# Order matters: core handles / and /dashboard, auth handles /login
app.include_router(auth_router)
app.include_router(member_router)  # Member routes first (more specific paths)
app.include_router(core_router)
app.include_router(members_router)
app.include_router(laufzettel_router)
app.include_router(catalog_router)
app.include_router(buchhaltung_router)
app.include_router(push_router)
app.include_router(shopify_router)
app.include_router(plane_router)


@app.get("/sw.js")
async def service_worker():
    # Service-Worker-Allowed: / lets the SW control the full origin
    # even though the file lives under /static/
    return FileResponse("static/sw.js", headers={"Service-Worker-Allowed": "/"})


@app.get("/offline.html")
async def offline_page(request: Request):
    """Serve offline fallback page for PWA service worker."""
    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse("offline.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "modules": ["auth", "core", "members", "laufzettel", "catalog", "push"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

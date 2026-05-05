"""MakerPi GroundControl - Modular FastAPI Application
Mounts all domain modules as separate route collections
"""

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from backend.config import SECRET_KEY
from backend.auth.routes import router as auth_router
from backend.members.routes import router as members_router
from backend.laufzettel.routes import router as laufzettel_router
from backend.catalog.routes import router as catalog_router
from backend.core.routes import router as core_router
from backend.member_routes import router as member_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup
app = FastAPI(title="MakerPi GroundControl")

# APScheduler setup for scheduled tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.members.easyverein import sync_members_from_easyverein

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
    scheduler.start()
    logger.info("APScheduler started with daily easyVerein sync at 03:00")


@app.on_event("shutdown")
async def shutdown_scheduler():
    """Shutdown the scheduler gracefully"""
    scheduler.shutdown()
    logger.info("APScheduler shutdown")


# Session middleware (required for auth)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "modules": ["auth", "core", "members", "laufzettel", "catalog"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

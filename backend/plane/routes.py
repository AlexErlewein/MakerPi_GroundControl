"""Plane issue tracker routes - public bug report submission"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import httpx
import logging

import backend.config as _cfg

router = APIRouter()
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")


class BugReportRequest(BaseModel):
    title: str
    description: str
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None


@router.get("/bug-report", response_class=HTMLResponse)
async def bug_report_page(request: Request):
    """Public bug report form - no login required"""
    plane_configured = bool(
        _cfg.PLANE_URL
        and _cfg.PLANE_API_TOKEN
        and _cfg.PLANE_WORKSPACE_SLUG
        and _cfg.PLANE_PROJECT_ID
    )
    return templates.TemplateResponse(
        "bug-report.html",
        {"request": request, "plane_configured": plane_configured},
    )


@router.post("/api/bug-report")
async def submit_bug_report(payload: BugReportRequest):
    """Submit a bug report as a Plane issue. No authentication required."""
    if not _cfg.PLANE_URL:
        raise HTTPException(status_code=503, detail="Bug reporting is not configured.")

    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="Title must not be empty.")
    if not payload.description.strip():
        raise HTTPException(status_code=422, detail="Description must not be empty.")

    # Build the issue description, appending reporter info if provided
    description_parts = [payload.description.strip()]
    if payload.reporter_name or payload.reporter_email:
        description_parts.append("\n---")
        description_parts.append("**Gemeldet von:**")
        if payload.reporter_name:
            description_parts.append(f"Name: {payload.reporter_name.strip()}")
        if payload.reporter_email:
            description_parts.append(f"E-Mail: {payload.reporter_email.strip()}")

    full_description = "\n".join(description_parts)

    url = (
        f"{_cfg.PLANE_URL.rstrip('/')}/api/v1/workspaces/"
        f"{_cfg.PLANE_WORKSPACE_SLUG}/projects/{_cfg.PLANE_PROJECT_ID}/issues/"
    )
    headers = {
        "X-API-Key": _cfg.PLANE_API_TOKEN,
        "Content-Type": "application/json",
    }
    body = {
        "name": payload.title.strip(),
        "description_html": f"<p>{full_description.replace(chr(10), '<br>')}</p>",
        "priority": "medium",
    }

    logger.info("Plane API POST → %s", url)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body, headers=headers)
    except httpx.RequestError as exc:
        logger.error("Plane API request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach Plane server.")

    logger.info("Plane API response: HTTP %s — %s", resp.status_code, resp.text[:500])
    if resp.status_code not in (200, 201):
        logger.error("Plane API error %s: %s", resp.status_code, resp.text)
        raise HTTPException(
            status_code=502,
            detail=f"Plane rejected the issue (HTTP {resp.status_code}): {resp.text[:200]}",
        )

    data = resp.json()
    logger.info("Plane issue created: %s", data.get("id"))
    return {
        "success": True,
        "issue_id": data.get("sequence_id") or data.get("id"),
    }

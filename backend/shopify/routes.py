"""Shopify routes - Gift card / voucher tracking via Shopify Admin API"""

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.config import SHOPIFY_ACCESS_TOKEN, SHOPIFY_STORE
from backend.auth.dependencies import check_auth

router = APIRouter()

_SHOPIFY_API_VERSION = "2024-04"


def _shopify_headers() -> dict:
    return {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def _shopify_url(path: str) -> str:
    return f"https://{SHOPIFY_STORE}/admin/api/{_SHOPIFY_API_VERSION}/{path}"


def _check_configured():
    if not SHOPIFY_STORE or not SHOPIFY_ACCESS_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Shopify not configured. Add shopify_store and shopify_access_token to config.json.",
        )


# ── Page ─────────────────────────────────────────────────────────────────────


@router.get("/shopify", response_class=HTMLResponse)
async def shopify_page(request: Request):
    """Render Shopify gift card tracking page"""
    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="templates")
    if not check_auth(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "shopify.html",
        {
            "request": request,
            "nav_active": "shopify",
            "current_user": request.session.get("user"),
            "shopify_configured": bool(SHOPIFY_STORE and SHOPIFY_ACCESS_TOKEN),
        },
    )


# ── Gift Cards API ────────────────────────────────────────────────────────────


@router.get("/api/shopify/gift-cards")
async def list_gift_cards(status: str = "enabled", limit: int = 250):
    """
    Fetch gift cards from Shopify.
    status: enabled | disabled | all
    """
    _check_configured()

    params = {"limit": min(limit, 250)}
    if status != "all":
        params["status"] = status

    all_cards = []
    url = _shopify_url("gift_cards.json")

    async with httpx.AsyncClient(timeout=20) as client:
        while url:
            resp = await client.get(url, headers=_shopify_headers(), params=params if url == _shopify_url("gift_cards.json") else {})
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Shopify API error: {resp.text}",
                )
            data = resp.json()
            cards = data.get("gift_cards", [])
            all_cards.extend(cards)

            # Handle pagination via Link header
            link_header = resp.headers.get("Link", "")
            next_url = None
            for part in link_header.split(","):
                part = part.strip()
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
                    break
            url = next_url

    result = []
    for c in all_cards:
        result.append(
            {
                "id": c["id"],
                "code": c.get("masked_code") or c.get("code", "****"),
                "initial_value": float(c.get("initial_value", 0)),
                "balance": float(c.get("balance", 0)),
                "currency": c.get("currency", "EUR"),
                "status": c.get("enabled", True) and "enabled" or "disabled",
                "created_at": c.get("created_at"),
                "expires_on": c.get("expires_on"),
                "customer_id": c.get("customer_id"),
                "note": c.get("note") or "",
                "last_characters": c.get("last_characters", ""),
            }
        )

    return {"gift_cards": result, "total": len(result)}


@router.get("/api/shopify/gift-cards/{gift_card_id}/transactions")
async def get_gift_card_transactions(gift_card_id: int):
    """Fetch transaction history for a specific gift card"""
    _check_configured()

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            _shopify_url(f"gift_cards/{gift_card_id}/transactions.json"),
            headers=_shopify_headers(),
        )
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Gift card not found")
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Shopify API error: {resp.text}",
            )

    transactions = resp.json().get("gift_card_transactions", [])
    result = []
    for t in transactions:
        result.append(
            {
                "id": t["id"],
                "gift_card_id": t.get("gift_card_id"),
                "amount": float(t.get("amount", 0)),
                "kind": t.get("kind", ""),  # credit | debit
                "created_at": t.get("created_at"),
                "order_id": t.get("order_id"),
                "note": t.get("note") or "",
            }
        )
    return {"transactions": result}


@router.get("/api/shopify/gift-cards/summary")
async def gift_card_summary():
    """Aggregate summary: total issued, total balance outstanding, total redeemed"""
    _check_configured()

    all_cards_resp = await list_gift_cards(status="all", limit=250)
    cards = all_cards_resp["gift_cards"]

    total_issued = sum(c["initial_value"] for c in cards)
    total_outstanding = sum(c["balance"] for c in cards if c["status"] == "enabled")
    total_redeemed = total_issued - sum(c["balance"] for c in cards)
    active_count = sum(1 for c in cards if c["status"] == "enabled" and c["balance"] > 0)

    return {
        "total_cards": len(cards),
        "active_cards": active_count,
        "total_issued_eur": round(total_issued, 2),
        "total_outstanding_eur": round(total_outstanding, 2),
        "total_redeemed_eur": round(total_redeemed, 2),
    }

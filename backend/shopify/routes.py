"""Shopify routes - Gift card / voucher tracking via Shopify Admin API"""

import logging
import time

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from backend.auth.dependencies import check_auth
from backend.config import (
    SHOPIFY_ACCESS_TOKEN,
    SHOPIFY_CLIENT_ID,
    SHOPIFY_CLIENT_SECRET,
    SHOPIFY_PHYSICAL_PRODUCT_ID,
    SHOPIFY_STORE,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_SHOPIFY_API_VERSION = "2024-04"

# ── Token cache (auto-refresh for Dev Dashboard apps) ─────────────────────────

_cached_token: str = SHOPIFY_ACCESS_TOKEN or ""
_token_expires_at: float = 0.0


async def _get_access_token() -> str:
    """Return a valid access token, refreshing via client_credentials grant if needed."""
    global _cached_token, _token_expires_at

    # Static token from config (legacy admin-created custom app)
    if SHOPIFY_ACCESS_TOKEN and not SHOPIFY_CLIENT_ID:
        return SHOPIFY_ACCESS_TOKEN

    # Refresh if expired or never fetched
    if not _cached_token or time.time() >= _token_expires_at:
        if not SHOPIFY_CLIENT_ID or not SHOPIFY_CLIENT_SECRET:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Shopify not configured. Set shopify_client_id and "
                    "shopify_client_secret (or shopify_access_token) in config.json."
                ),
            )
        token_url = f"https://{SHOPIFY_STORE}/admin/oauth/access_token"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": SHOPIFY_CLIENT_ID,
                        "client_secret": SHOPIFY_CLIENT_SECRET,
                    },
                )
            if resp.status_code != 200:
                logger.error(
                    "Shopify token refresh failed: %s %s", resp.status_code, resp.text
                )
                raise HTTPException(
                    status_code=503,
                    detail=f"Shopify token refresh failed: {resp.status_code} {resp.text}",
                )
            data = resp.json()
            _cached_token = data["access_token"]
            _token_expires_at = (
                time.time() + data.get("expires_in", 86399) - 300
            )  # refresh 5 min early
            logger.info(
                "Shopify access token refreshed, expires in %ss", data.get("expires_in")
            )
        except httpx.HTTPError as exc:
            logger.error("Shopify token refresh error: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Shopify token refresh error: {exc}",
            )

    return _cached_token


def _shopify_url(path: str) -> str:
    return f"https://{SHOPIFY_STORE}/admin/api/{_SHOPIFY_API_VERSION}/{path}"


def _graphql_url() -> str:
    return f"https://{SHOPIFY_STORE}/admin/api/{_SHOPIFY_API_VERSION}/graphql.json"


def _is_configured() -> bool:
    """Check if Shopify is configured with either static token or OAuth credentials."""
    return bool(
        SHOPIFY_STORE
        and (SHOPIFY_ACCESS_TOKEN or (SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET))
    )


async def _graphql_query(query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query against the Shopify Admin API."""
    token = await _get_access_token()
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            _graphql_url(),
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Shopify GraphQL error: {resp.text}",
        )
    data = resp.json()
    if "errors" in data:
        msgs = "; ".join(e.get("message", "") for e in data["errors"])
        raise HTTPException(status_code=400, detail=f"Shopify GraphQL: {msgs}")
    return data.get("data", {})


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
            "shopify_configured": _is_configured(),
        },
    )


# ── Gift Cards API ────────────────────────────────────────────────────────────


@router.get("/api/shopify/gift-cards")
async def list_gift_cards(status: str = "enabled", limit: int = 250):
    """
    Fetch gift cards from Shopify.
    status: enabled | disabled | all
    """
    token = await _get_access_token()
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}

    params = {"limit": min(limit, 250)}
    if status != "all":
        params["status"] = status

    all_cards = []
    url = _shopify_url("gift_cards.json")

    async with httpx.AsyncClient(timeout=20) as client:
        while url:
            resp = await client.get(
                url,
                headers=headers,
                params=params if url == _shopify_url("gift_cards.json") else {},
            )
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


# ── Physical Gift Card Product ────────────────────────────────────────────────


@router.get("/api/shopify/physical-product")
async def get_physical_product():
    """Fetch the physical gift card product with variant stock levels via GraphQL."""
    if not SHOPIFY_PHYSICAL_PRODUCT_ID:
        return {"configured": False, "product": None}

    query = """
    query($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        status
        featuredImage { url }
        variants(first: 50) {
          edges {
            node {
              id
              title
              price
              availableForSale
              inventoryQuantity
              selectedOptions { name value }
            }
          }
        }
      }
    }
    """
    try:
        data = await _graphql_query(query, {"id": SHOPIFY_PHYSICAL_PRODUCT_ID})
    except HTTPException:
        return {"configured": True, "product": None, "error": "Shopify API error"}

    p = data.get("product")
    if not p:
        return {"configured": True, "product": None, "error": "Product not found"}

    variants = []
    total_stock = 0
    for edge in p.get("variants", {}).get("edges", []):
        v = edge["node"]
        qty = v.get("inventoryQuantity", 0)
        total_stock += qty
        # Parse "10€ (15€)" format: nominal value and actual price
        title = v.get("title", "")
        variants.append(
            {
                "id": v["id"],
                "title": title,
                "price": float(v.get("price", 0)),
                "available": v.get("availableForSale", False),
                "stock": qty,
            }
        )

    return {
        "configured": True,
        "product": {
            "id": p["id"],
            "title": p["title"],
            "handle": p["handle"],
            "status": p["status"],
            "image": (p.get("featuredImage") or {}).get("url", ""),
            "url": f"https://{SHOPIFY_STORE}/products/{p['handle']}",
            "variants": variants,
            "total_stock": total_stock,
            "total_variants": len(variants),
            "available_variants": sum(1 for v in variants if v["available"]),
        },
    }


# ── Physical Gift Card Orders ─────────────────────────────────────────────────


@router.get("/api/shopify/physical-product/orders")
async def list_physical_product_orders(limit: int = 50):
    """Fetch orders containing the physical gift card product, with notes."""
    if not SHOPIFY_PHYSICAL_PRODUCT_ID:
        return {"configured": False, "orders": [], "has_next": False}

    query = """
    query($query: String!, $limit: Int!) {
      orders(first: $limit, reverse: true, query: $query) {
        edges {
          node {
            id
            name
            createdAt
            note
            displayFinancialStatus
            customer { firstName lastName email }
            lineItems(first: 20) {
              edges {
                node {
                  id
                  title
                  variantTitle
                  quantity
                }
              }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    try:
        data = await _graphql_query(
            query,
            {
                "query": f"product_id:{SHOPIFY_PHYSICAL_PRODUCT_ID.split('/')[-1]}",
                "limit": min(limit, 250),
            },
        )
    except HTTPException as exc:
        logger.error("Physical product orders fetch error: %s", exc)
        return {
            "configured": True,
            "orders": [],
            "has_next": False,
            "error": str(exc.detail),
        }

    orders_conn = data.get("orders", {})
    edges = orders_conn.get("edges") or []
    page_info = orders_conn.get("pageInfo") or {}

    orders = []
    for edge in edges:
        o = edge["node"]
        # Only include orders that actually have the physical gift card line item
        gc_line = None
        for li in (o.get("lineItems") or {}).get("edges") or []:
            item = li["node"]
            if (
                "physischer" in item.get("title", "").lower()
                and "geschenk" in item.get("title", "").lower()
            ):
                gc_line = item
                break

        if not gc_line:
            continue

        customer = o.get("customer")
        orders.append(
            {
                "id": o["id"],
                "name": o.get("name", ""),
                "created_at": o.get("createdAt"),
                "note": o.get("note") or "",
                "financial_status": o.get("displayFinancialStatus", ""),
                "customer": {
                    "name": (
                        f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip()
                        if customer
                        else ""
                    ),
                    "email": customer.get("email") if customer else None,
                },
                "variant": gc_line.get("variantTitle", gc_line.get("title", "")),
                "quantity": gc_line.get("quantity", 1),
                "shopify_order_id": o["id"].split("/")[-1],
            }
        )

    return {
        "configured": True,
        "orders": orders,
        "has_next": page_info.get("hasNextPage", False),
        "total": len(orders),
    }


@router.put("/api/shopify/physical-product/orders/{order_id}/note")
async def update_physical_product_order_note(order_id: str, body: NoteUpdate):
    """Update the note on a Shopify order (requires write_orders scope)."""
    gid = f"gid://shopify/Order/{order_id}"

    mutation = """
    mutation($id: ID!, $note: String) {
      orderUpdate(input: {id: $id, note: $note}) {
        order { id note }
        userErrors { field message }
      }
    }
    """
    try:
        data = await _graphql_query(
            mutation,
            {
                "id": gid,
                "note": body.note if body.note.strip() else None,
            },
        )
    except HTTPException as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=f"Shopify order update failed: {exc.detail}",
        )

    result = data.get("orderUpdate", {})
    errors = result.get("userErrors", [])
    if errors:
        msgs = "; ".join(e.get("message", "") for e in errors)
        raise HTTPException(status_code=400, detail=f"Shopify: {msgs}")

    order = result.get("order") or {}
    return {"note": order.get("note") or ""}


# ── Summary (must be before {gift_card_id} to avoid route conflict) ──────────


@router.get("/api/shopify/gift-cards/summary")
async def gift_card_summary():
    """Aggregate summary: total issued, total balance outstanding, total redeemed"""
    all_cards_resp = await list_gift_cards(status="all", limit=250)
    cards = all_cards_resp["gift_cards"]

    total_issued = sum(c["initial_value"] for c in cards)
    total_outstanding = sum(c["balance"] for c in cards if c["status"] == "enabled")
    total_redeemed = total_issued - sum(c["balance"] for c in cards)
    active_count = sum(
        1 for c in cards if c["status"] == "enabled" and c["balance"] > 0
    )

    return {
        "total_cards": len(cards),
        "active_cards": active_count,
        "total_issued_eur": round(total_issued, 2),
        "total_outstanding_eur": round(total_outstanding, 2),
        "total_redeemed_eur": round(total_redeemed, 2),
    }


# ── Gift Card Detail (GraphQL) ────────────────────────────────────────────────


_GIFT_CARD_DETAIL_FRAGMENT = """
fragment GiftCardDetail on GiftCard {
  id
  lastCharacters
  balance { amount currencyCode }
  initialValue { amount currencyCode }
  createdAt
  updatedAt
  expiresOn
  enabled
  note
  customer {
    id
    firstName
    lastName
    email
  }
  transactions(first: 50) {
    edges {
      node {
        id
        amount { amount currencyCode }
        note
        processedAt
      }
    }
  }
}
"""


@router.get("/api/shopify/gift-cards/{gift_card_id}")
async def get_gift_card_detail(gift_card_id: int):
    """Fetch full gift card detail including customer and transactions via GraphQL."""
    query = f"""
    {{ giftCard(id: "gid://shopify/GiftCard/{gift_card_id}") {{
      ...GiftCardDetail
    }} }}
    {_GIFT_CARD_DETAIL_FRAGMENT}
    """
    try:
        data = await _graphql_query(query)
    except HTTPException as exc:
        if exc.status_code == 400 and "not found" in exc.detail.lower():
            raise HTTPException(status_code=404, detail="Gift card not found")
        raise

    gc = data.get("giftCard")
    if not gc:
        raise HTTPException(status_code=404, detail="Gift card not found")

    balance = gc.get("balance", {}) or {}
    initial = gc.get("initialValue", {}) or {}
    customer = gc.get("customer")

    tx_edges = (gc.get("transactions") or {}).get("edges") or []
    transactions = []
    for edge in tx_edges:
        node = edge.get("node", {})
        amt = (node.get("amount") or {}).get("amount", "0")
        transactions.append(
            {
                "id": node.get("id"),
                "amount": float(amt),
                "currency": (node.get("amount") or {}).get("currencyCode", "EUR"),
                "note": node.get("note") or "",
                "processed_at": node.get("processedAt"),
            }
        )

    return {
        "id": gift_card_id,
        "last_characters": gc.get("lastCharacters", ""),
        "balance": float(balance.get("amount", 0)),
        "currency": balance.get("currencyCode", "EUR"),
        "initial_value": float(initial.get("amount", 0)),
        "enabled": gc.get("enabled", True),
        "created_at": gc.get("createdAt"),
        "updated_at": gc.get("updatedAt"),
        "expires_on": gc.get("expiresOn"),
        "note": gc.get("note") or "",
        "customer": {
            "id": customer.get("id"),
            "name": f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
            "email": customer.get("email"),
        }
        if customer
        else None,
        "transactions": transactions,
    }


# ── Gift Card Transactions (GraphQL fallback) ────────────────────────────────


@router.get("/api/shopify/gift-cards/{gift_card_id}/transactions")
async def get_gift_card_transactions(gift_card_id: int):
    """Fetch transaction history for a specific gift card via GraphQL."""
    query = """
    query($id: ID!) {
      giftCard(id: $id) {
        transactions(first: 50) {
          edges {
            node {
              id
              amount { amount currencyCode }
              note
              processedAt
            }
          }
        }
      }
    }
    """
    try:
        data = await _graphql_query(
            query, {"id": f"gid://shopify/GiftCard/{gift_card_id}"}
        )
    except HTTPException as exc:
        if exc.status_code == 400 and "not found" in exc.detail.lower():
            raise HTTPException(status_code=404, detail="Gift card not found")
        raise

    gc = data.get("giftCard")
    if not gc:
        raise HTTPException(status_code=404, detail="Gift card not found")

    tx_edges = (gc.get("transactions") or {}).get("edges") or []
    transactions = []
    for edge in tx_edges:
        node = edge.get("node", {})
        amt = (node.get("amount") or {}).get("amount", "0")
        transactions.append(
            {
                "id": node.get("id"),
                "amount": float(amt),
                "currency": (node.get("amount") or {}).get("currencyCode", "EUR"),
                "note": node.get("note") or "",
                "processed_at": node.get("processedAt"),
            }
        )
    return {"transactions": transactions}


# ── Update Gift Card Note ────────────────────────────────────────────────────


class NoteUpdate(BaseModel):
    note: str


@router.put("/api/shopify/gift-cards/{gift_card_id}/note")
async def update_gift_card_note(gift_card_id: int, body: NoteUpdate):
    """Update the merchant note on a gift card via REST API."""
    token = await _get_access_token()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.put(
            _shopify_url(f"gift_cards/{gift_card_id}.json"),
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
            },
            json={
                "gift_card": {
                    "id": gift_card_id,
                    "note": body.note if body.note.strip() else None,
                }
            },
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Shopify API error: {resp.text}",
        )
    gc = resp.json().get("gift_card", {})
    return {"note": gc.get("note") or ""}


# ── Adjust Gift Card Balance ─────────────────────────────────────────────────


class BalanceAdjust(BaseModel):
    amount: float
    note: str = ""


@router.post("/api/shopify/gift-cards/{gift_card_id}/adjust")
async def adjust_gift_card_balance(gift_card_id: int, body: BalanceAdjust):
    """Adjust a gift card balance (positive = credit, negative = debit) via GraphQL."""
    gid = f"gid://shopify/GiftCard/{gift_card_id}"
    note_val = body.note if body.note.strip() else None

    if body.amount > 0:
        mutation = """
        mutation($id: ID!, $amount: MoneyInput!, $note: String) {
          giftCardCredit(id: $id, creditInput: {creditAmount: $amount, note: $note}) {
            giftCardCreditTransaction { amount { amount currencyCode } }
            userErrors { field message }
          }
        }
        """
        result_key = "giftCardCredit"
        tx_key = "giftCardCreditTransaction"
    elif body.amount < 0:
        mutation = """
        mutation($id: ID!, $amount: MoneyInput!, $note: String) {
          giftCardDebit(id: $id, debitInput: {debitAmount: $amount, note: $note}) {
            giftCardDebitTransaction { amount { amount currencyCode } }
            userErrors { field message }
          }
        }
        """
        result_key = "giftCardDebit"
        tx_key = "giftCardDebitTransaction"
    else:
        raise HTTPException(status_code=400, detail="Amount must not be zero")

    variables = {
        "id": gid,
        "amount": {"amount": str(abs(body.amount)), "currencyCode": "EUR"},
        "note": note_val,
    }

    data = await _graphql_query(mutation, variables)

    result = data.get(result_key, {})
    errors = result.get("userErrors", [])
    if errors:
        msgs = "; ".join(e.get("message", "") for e in errors)
        raise HTTPException(status_code=400, detail=f"Shopify: {msgs}")

    adj = result.get(tx_key, {})
    amt = (adj.get("amount") or {}).get("amount", "0")
    return {
        "amount": float(amt),
        "currency": (adj.get("amount") or {}).get("currencyCode", "EUR"),
    }


# ── Deactivate / Reactivate Gift Card ────────────────────────────────────────


@router.post("/api/shopify/gift-cards/{gift_card_id}/toggle")
async def toggle_gift_card_status(gift_card_id: int):
    """Toggle a gift card between enabled and disabled via GraphQL."""
    gid = f"gid://shopify/GiftCard/{gift_card_id}"

    # Determine current state by checking disabledAt via GraphQL
    query_check = """
    query($id: ID!) {
      giftCard(id: $id) {
        disabledAt
      }
    }
    """
    data = await _graphql_query(
        query_check, {"id": f"gid://shopify/GiftCard/{gift_card_id}"}
    )
    gc = data.get("giftCard", {})
    is_disabled = gc.get("disabledAt") is not None

    if is_disabled:
        # Reactivate via giftCardUpdate
        mutation = """
        mutation($id: ID!, $input: GiftCardUpdateInput!) {
          giftCardUpdate(id: $id, input: $input) {
            giftCard { disabledAt }
            userErrors { field message }
          }
        }
        """
        variables = {"id": gid, "input": {}}
        data = await _graphql_query(mutation, variables)
        result = data.get("giftCardUpdate", {})
    else:
        mutation = """
        mutation($id: ID!) {
          giftCardDeactivate(id: $id) {
            giftCard { disabledAt }
            userErrors { field message }
          }
        }
        """
        variables = {"id": gid}
        data = await _graphql_query(mutation, variables)
        result = data.get("giftCardDeactivate", {})

    errors = result.get("userErrors", [])
    if errors:
        msgs = "; ".join(e.get("message", "") for e in errors)
        raise HTTPException(status_code=400, detail=f"Shopify: {msgs}")

    new_disabled = (result.get("giftCard") or {}).get("disabledAt")
    return {"disabled": new_disabled is not None}

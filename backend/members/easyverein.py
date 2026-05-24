"""easyVerein sync service - fetches members from easyVerein API v2.0"""

import logging
import asyncio
from datetime import datetime, timezone, date
from typing import Optional
import httpx

from backend.config import EASYVEREIN_API_KEY, EASYVEREIN_ORG_ID
from .models import Mitglied
from .db import SessionLocal

logger = logging.getLogger(__name__)

EASYVEREIN_API_BASE = "https://easyverein.com/api/v2.0"

# Rate limiting settings - CONSERVATIVE to avoid 429 errors
PAGE_SIZE = 10  # Very small pages to avoid disconnection
REQUEST_DELAY = 5.0  # 5 seconds between page requests
MAX_RETRIES = 3
RETRY_DELAY = 15  # 15 seconds to wait after errors (exponential: 15, 30, 45...)

# Track sync status in memory (could be persisted to DB if needed)
_last_sync_result: Optional[dict] = None


async def fetch_with_retry(
    client: httpx.AsyncClient, url: str, headers: dict, params: Optional[dict] = None
) -> httpx.Response:
    """Fetch URL with retry logic for rate limiting (429) and disconnection errors"""
    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 429:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    f"Rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}"
                )
                await asyncio.sleep(wait_time)  # Exponential backoff
                continue
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            last_exception = e
            if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    f"Rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}"
                )
                await asyncio.sleep(wait_time)
                continue
            raise
        except httpx.RemoteProtocolError as e:
            # Server disconnected without response - retry with longer delay
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    f"Server disconnected, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}"
                )
                await asyncio.sleep(wait_time)
                continue
            raise
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    f"Request failed ({type(e).__name__}), waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}"
                )
                await asyncio.sleep(wait_time)
                continue
            raise
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    raise httpx.HTTPStatusError("Max retries exceeded", request=None, response=None)


def get_auth_headers() -> dict:
    """Get authorization headers for easyVerein API"""
    if not EASYVEREIN_API_KEY:
        raise ValueError("easyverein_api_key not configured")
    return {
        "Authorization": f"Bearer {EASYVEREIN_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def post_with_retry(
    client: httpx.AsyncClient, url: str, headers: dict, json_data: dict
) -> httpx.Response:
    """POST with retry logic for rate limiting and disconnection errors"""
    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.post(url, headers=headers, json=json_data)
            if response.status_code == 429:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    f"Rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}"
                )
                await asyncio.sleep(wait_time)
                continue
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            last_exception = e
            if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    f"Rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}"
                )
                await asyncio.sleep(wait_time)
                continue
            raise
        except httpx.RemoteProtocolError as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    f"Server disconnected, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}"
                )
                await asyncio.sleep(wait_time)
                continue
            raise
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    f"Request failed ({type(e).__name__}), waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}"
                )
                await asyncio.sleep(wait_time)
                continue
            raise
    if last_exception:
        raise last_exception
    raise RuntimeError("Max retries exceeded")


async def create_member_application(data: dict) -> dict:
    """Create a new member application in easyVerein (two-step: contact-details then member).

    data keys: first_name, family_name, email, salutation (optional), date_of_birth (optional),
               mobile_phone (optional), private_phone (optional), street (optional),
               zip_code (optional), city (optional), country (optional), iban (optional),
               method_of_payment (optional int), payment_amount (optional float),
               payment_interval_months (optional int)

    Returns dict with ev_member_id, ev_contact_id, membership_number.
    Raises ValueError if API key not configured.
    Raises httpx.HTTPStatusError on API failure.
    """
    from backend.config import EASYVEREIN_REGISTRATION_MOCK

    if EASYVEREIN_REGISTRATION_MOCK:
        logger.info("easyVerein registration mock mode: skipping real API call")
        return {
            "ev_member_id": 99999,
            "ev_contact_id": 88888,
            "membership_number": "MOCK-001",
        }

    headers = get_auth_headers()  # raises ValueError if no API key

    timeout = httpx.Timeout(60.0, connect=30.0)
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        # Step 1: Create contact-details
        contact_payload: dict = {"isCompany": False}
        if data.get("salutation"):
            contact_payload["salutation"] = data["salutation"]
        if data.get("first_name"):
            contact_payload["firstName"] = data["first_name"]
        if data.get("family_name"):
            contact_payload["familyName"] = data["family_name"]
        if data.get("email"):
            contact_payload["privateEmail"] = data["email"]
        if data.get("mobile_phone"):
            contact_payload["mobilePhone"] = data["mobile_phone"]
        if data.get("private_phone"):
            contact_payload["privatePhone"] = data["private_phone"]
        if data.get("date_of_birth"):
            contact_payload["dateOfBirth"] = data["date_of_birth"]
        if data.get("street"):
            contact_payload["street"] = data["street"]
        if data.get("zip_code"):
            contact_payload["zip"] = data["zip_code"]
        if data.get("city"):
            contact_payload["city"] = data["city"]
        if data.get("country"):
            contact_payload["country"] = data["country"]
        if data.get("iban"):
            contact_payload["iban"] = data["iban"]
        if data.get("method_of_payment") is not None:
            contact_payload["methodOfPayment"] = data["method_of_payment"]

        logger.info(f"Creating easyVerein contact-details for {data.get('email')}")
        contact_resp = await post_with_retry(
            client, f"{EASYVEREIN_API_BASE}/contact-details/", headers, contact_payload
        )
        contact_data = contact_resp.json()
        contact_url = contact_data.get("url") or contact_data.get("id")
        if not contact_url:
            raise ValueError(
                f"easyVerein contact-details response missing 'url': {contact_data}"
            )

        logger.info(f"Created contact-details: {contact_url}")

        # Step 2: Create member
        member_payload: dict = {
            "emailOrUserName": data["email"],
            "contactDetails": contact_url,
            "isApplication": True,
        }
        if data.get("membership_group_url"):
            member_payload["memberGroups"] = [data["membership_group_url"]]
        if data.get("payment_amount") is not None:
            member_payload["paymentAmount"] = data["payment_amount"]
        if data.get("payment_interval_months") is not None:
            member_payload["paymentIntervallMonths"] = data["payment_interval_months"]

        logger.info(f"Creating easyVerein member for {data.get('email')}")
        member_resp = await post_with_retry(
            client, f"{EASYVEREIN_API_BASE}/member/", headers, member_payload
        )
        member_data = member_resp.json()

        ev_member_id = member_data.get("id")
        membership_number = member_data.get("membershipNumber") or str(ev_member_id)
        contact_id = contact_data.get("id")

        logger.info(
            f"Created easyVerein member {ev_member_id} (membership_number={membership_number})"
        )

        return {
            "ev_member_id": ev_member_id,
            "ev_contact_id": contact_id,
            "membership_number": str(membership_number) if membership_number else None,
        }


def get_sync_status() -> dict:
    """Get the last sync status"""
    global _last_sync_result
    if _last_sync_result is None:
        return {
            "last_sync": None,
            "success": None,
            "message": "No sync performed yet",
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
    return _last_sync_result


async def fetch_contact_details(
    client: httpx.AsyncClient, headers: dict, contact_url: str
) -> Optional[dict]:
    """Fetch contact details for a member"""
    try:
        response = await client.get(contact_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch contact details from {contact_url}: {e}")
        return None


def map_easyverein_member(
    ev_member: dict, contact_details: Optional[dict]
) -> Optional[dict]:
    """Map easyVerein member data to GroundControl Mitglied format"""
    try:
        # Member ID is in membershipNumber field
        member_id_raw = ev_member.get("membershipNumber")
        if not member_id_raw:
            logger.warning(
                f"Skipping member without membershipNumber: {ev_member.get('id')}"
            )
            return None
        member_id = str(member_id_raw).strip()

        # Name comes from contactDetails - prioritize firstName + familyName
        name = None
        if contact_details:
            # Prefer combining firstName + familyName (individual fields)
            first = contact_details.get("firstName", "").strip()
            family = contact_details.get("familyName", "").strip()
            if first or family:
                name = f"{first} {family}".strip()
            # Fallback to aggregated name field if individual fields are empty
            if not name:
                name = contact_details.get("name", "").strip()

        if not name:
            # Last resort: use emailOrUserName or skip
            name = ev_member.get("emailOrUserName", "").strip()
            if not name:
                logger.warning(f"Skipping member without name: {member_id}")
                return None

        # Email from contactDetails
        email = None
        if contact_details:
            email = (
                contact_details.get("email")
                or contact_details.get("privateEmail")
                or contact_details.get("companyEmail")
            )
        if not email:
            email = ev_member.get("emailOrUserName")

        # Phone from contactDetails
        phone = None
        if contact_details:
            phone = contact_details.get("mobilePhone") or contact_details.get("phone")

        # Determine status from various fields
        # Active if: not an application, no resignation date, not blocked
        status = "active"
        if ev_member.get("_isApplication"):
            status = "inactive"  # Applications are not full members yet
        elif ev_member.get("resignationDate"):
            status = "inactive"  # Member has resigned
        elif ev_member.get("_isBlocked"):
            status = "inactive"  # Blocked member

        # Join date
        joined_date = None
        join_date_str = ev_member.get("joinDate")
        if join_date_str:
            try:
                # Parse ISO format date (2025-07-17T00:00:00+02:00)
                joined_date = date.fromisoformat(join_date_str[:10])
            except (ValueError, IndexError):
                pass

        return {
            "member_id": member_id,
            "name": name,
            "email": email.strip() if email else None,
            "phone": phone.strip() if phone else None,
            "status": status,
            "joined_date": joined_date,
            "notes": None,
        }
    except Exception as e:
        logger.error(f"Error mapping member {ev_member}: {e}")
        return None


async def sync_members_from_easyverein() -> dict:
    """Sync members from easyVerein API to local database"""
    global _last_sync_result

    if not EASYVEREIN_API_KEY:
        result = {
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "success": False,
            "message": "easyverein_api_key not configured",
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
        _last_sync_result = result
        return result

    created_count = 0
    updated_count = 0
    error_count = 0
    skipped_count = 0

    try:
        headers = get_auth_headers()
        ev_members = []

        # Configure timeout and connection limits to prevent disconnection
        timeout = httpx.Timeout(60.0, connect=30.0)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            # Build URL with optional org ID and smaller page size (rate limiting)
            url = f"{EASYVEREIN_API_BASE}/member/"
            params = {"page_size": PAGE_SIZE}  # Smaller pages to avoid rate limits
            if EASYVEREIN_ORG_ID:
                params["organization"] = EASYVEREIN_ORG_ID

            # Fetch all pages with rate limiting
            next_url = url
            page_count = 0
            while next_url:
                page_count += 1
                logger.info(
                    f"Fetching members from easyVerein: {next_url} (params: {params}) - page {page_count}"
                )
                try:
                    response = await fetch_with_retry(
                        client, next_url, headers, params if next_url == url else None
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch page {page_count}: {e}")
                    raise

                # Rate limiting: wait between requests
                if next_url != url:
                    await asyncio.sleep(REQUEST_DELAY)

                data = response.json()

                # Handle both list and paginated response
                if isinstance(data, list):
                    page_members = data
                    next_url = None  # No pagination for list response
                elif isinstance(data, dict) and "results" in data:
                    page_members = data["results"]
                    next_url = data.get("next")  # Get next page URL if exists
                else:
                    page_members = []
                    next_url = None

                ev_members.extend(page_members)
                logger.info(
                    f"Fetched {len(page_members)} members (total: {len(ev_members)})"
                )

                # Safety limit - don't fetch more than 1000 members
                if len(ev_members) >= 1000:
                    logger.warning("Reached 1000 member limit, stopping pagination")
                    break

            logger.info(f"Total members fetched from easyVerein: {len(ev_members)}")

            # Get database session
            db = SessionLocal()
            try:
                for ev_member in ev_members:
                    try:
                        # Fetch contact details if URL is available (with rate limiting)
                        contact_details = None
                        contact_url = ev_member.get("contactDetails")
                        if contact_url and isinstance(contact_url, str):
                            contact_details = await fetch_contact_details(
                                client, headers, contact_url
                            )
                            await asyncio.sleep(
                                1.0
                            )  # 1 second delay between contact detail requests

                        mapped = map_easyverein_member(ev_member, contact_details)
                        if not mapped:
                            skipped_count += 1
                            continue

                        # Check if member already exists by member_id
                        existing = (
                            db.query(Mitglied)
                            .filter(Mitglied.member_id == mapped["member_id"])
                            .first()
                        )

                        if existing:
                            # Update existing member
                            existing.name = mapped["name"]
                            if mapped["email"]:
                                existing.email = mapped["email"]
                            if mapped["phone"]:
                                existing.phone = mapped["phone"]
                            existing.status = mapped["status"]
                            if mapped["joined_date"]:
                                existing.joined_date = mapped["joined_date"]
                            updated_count += 1
                        else:
                            # Create new member
                            new_member = Mitglied(**mapped)
                            db.add(new_member)
                            created_count += 1

                    except Exception as e:
                        logger.error(
                            f"Error processing member {ev_member.get('id')}: {e}"
                        )
                        error_count += 1

                db.commit()
                logger.info(
                    f"Sync complete: {created_count} created, {updated_count} updated, {skipped_count} skipped, {error_count} errors"
                )

            finally:
                db.close()

        result = {
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "success": True,
            "message": f"Synced {created_count} new, {updated_count} updated, {skipped_count} skipped, {error_count} errors",
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": error_count,
        }
        _last_sync_result = result
        return result

    except httpx.HTTPStatusError as e:
        if e.response is not None:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text[:200]}"
        else:
            error_msg = f"HTTP error: {str(e)}"
        logger.error(error_msg)
        result = {
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "success": False,
            "message": error_msg,
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": error_count + 1,
        }
        _last_sync_result = result
        return result

    except Exception as e:
        error_msg = f"Sync failed: {str(e)}"
        logger.error(error_msg)
        result = {
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "success": False,
            "message": error_msg,
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": error_count + 1,
        }
        _last_sync_result = result
        return result

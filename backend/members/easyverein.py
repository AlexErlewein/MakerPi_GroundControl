"""easyVerein sync service - fetches members from easyVerein API v2.0"""

import logging
from datetime import datetime, timezone, date
from typing import Optional
import httpx

from backend.config import EASYVEREIN_API_KEY, EASYVEREIN_ORG_ID
from .models import Mitglied
from .db import SessionLocal

logger = logging.getLogger(__name__)

EASYVEREIN_API_BASE = "https://easyverein.com/api/v2.0"

# Track sync status in memory (could be persisted to DB if needed)
_last_sync_result: Optional[dict] = None


def get_auth_headers() -> dict:
    """Get authorization headers for easyVerein API"""
    if not EASYVEREIN_API_KEY:
        raise ValueError("easyverein_api_key not configured")
    return {
        "Authorization": f"Bearer {EASYVEREIN_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
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


async def fetch_contact_details(client: httpx.AsyncClient, headers: dict, contact_url: str) -> Optional[dict]:
    """Fetch contact details for a member"""
    try:
        response = await client.get(contact_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch contact details from {contact_url}: {e}")
        return None


def map_easyverein_member(ev_member: dict, contact_details: Optional[dict]) -> Optional[dict]:
    """Map easyVerein member data to GroundControl Mitglied format"""
    try:
        # Member ID is in membershipNumber field
        member_id_raw = ev_member.get("membershipNumber")
        if not member_id_raw:
            logger.warning(f"Skipping member without membershipNumber: {ev_member.get('id')}")
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
            email = contact_details.get("email") or contact_details.get("privateEmail") or contact_details.get("companyEmail")
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
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Build URL with optional org ID and high page size
            url = f"{EASYVEREIN_API_BASE}/member/"
            params = {"page_size": 200}  # Fetch up to 200 members per page
            if EASYVEREIN_ORG_ID:
                params["organization"] = EASYVEREIN_ORG_ID
            
            # Fetch all pages
            next_url = url
            while next_url:
                logger.info(f"Fetching members from easyVerein: {next_url} (params: {params})")
                response = await client.get(next_url, headers=headers, params=params if next_url == url else None)
                response.raise_for_status()
                
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
                logger.info(f"Fetched {len(page_members)} members (total: {len(ev_members)})")
                
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
                        # Fetch contact details if URL is available
                        contact_details = None
                        contact_url = ev_member.get("contactDetails")
                        if contact_url and isinstance(contact_url, str):
                            contact_details = await fetch_contact_details(client, headers, contact_url)
                        
                        mapped = map_easyverein_member(ev_member, contact_details)
                        if not mapped:
                            skipped_count += 1
                            continue
                        
                        # Check if member already exists by member_id
                        existing = db.query(Mitglied).filter(
                            Mitglied.member_id == mapped["member_id"]
                        ).first()
                        
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
                        logger.error(f"Error processing member {ev_member.get('id')}: {e}")
                        error_count += 1
                
                db.commit()
                logger.info(f"Sync complete: {created_count} created, {updated_count} updated, {skipped_count} skipped, {error_count} errors")
                
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
        error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
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

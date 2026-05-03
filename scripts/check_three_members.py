#!/usr/bin/env python3
"""Check specific member IDs 179, 25, 37 in easyVerein API"""
import sys
import asyncio
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from backend.config import EASYVEREIN_API_KEY, EASYVEREIN_ORG_ID

EASYVEREIN_API_BASE = "https://easyverein.com/api/v2.0"
TARGET_IDS = ["179", "25", "37"]

async def check_members():
    headers = {
        "Authorization": f"Bearer {EASYVEREIN_API_KEY}",
        "Accept": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch all members (need to find by membershipNumber)
        url = f"{EASYVEREIN_API_BASE}/member/"
        params = {"page_size": 200}
        if EASYVEREIN_ORG_ID:
            params["organization"] = EASYVEREIN_ORG_ID
        
        print("Fetching members...")
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        members = data.get("results", []) if isinstance(data, dict) else data
        
        print(f"Total members fetched: {len(members)}\n")
        
        # Find target members
        for m in members:
            member_id = str(m.get("membershipNumber", ""))
            if member_id not in TARGET_IDS:
                continue
            
            contact_url = m.get("contactDetails")
            email_or_user = m.get("emailOrUserName", "")
            
            print(f"=== Member ID: {member_id} ===")
            print(f"  emailOrUserName: {email_or_user}")
            
            if contact_url:
                try:
                    cresp = await client.get(contact_url, headers=headers)
                    c = cresp.json()
                    
                    name = c.get("name", "").strip()
                    first = c.get("firstName", "").strip()
                    family = c.get("familyName", "").strip()
                    email = c.get("email", "").strip() or c.get("privateEmail", "").strip()
                    
                    print(f"  contactDetails.name: '{name}'")
                    print(f"  contactDetails.firstName: '{first}'")
                    print(f"  contactDetails.familyName: '{family}'")
                    print(f"  contactDetails.email: '{email}'")
                    print(f"  --> Mapped name would be: '{first} {family}'.strip() or '{name}'")
                    
                except Exception as e:
                    print(f"  ERROR fetching contact: {e}")
            else:
                print("  NO contactDetails URL")
            print()

if __name__ == "__main__":
    asyncio.run(check_members())

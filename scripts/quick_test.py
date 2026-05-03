#!/usr/bin/env python3
"""Quick test - fetch 5 members and show name mapping"""
import sys
import asyncio
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from backend.config import EASYVEREIN_API_KEY, EASYVEREIN_ORG_ID

EASYVEREIN_API_BASE = "https://easyverein.com/api/v2.0"

async def test():
    headers = {
        "Authorization": f"Bearer {EASYVEREIN_API_KEY}",
        "Accept": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch first page only
        url = f"{EASYVEREIN_API_BASE}/member/"
        params = {"page_size": 5}
        if EASYVEREIN_ORG_ID:
            params["organization"] = EASYVEREIN_ORG_ID
        
        print(f"Fetching from: {url}")
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        members = data.get("results", []) if isinstance(data, dict) else data
        
        print(f"\nFetched {len(members)} members:\n")
        
        for m in members:
            member_id = m.get("membershipNumber")
            contact_url = m.get("contactDetails")
            
            # Fetch contact details
            name = "N/A"
            first = ""
            family = ""
            email = m.get("emailOrUserName", "")
            
            if contact_url:
                try:
                    cresp = await client.get(contact_url, headers=headers)
                    c = cresp.json()
                    first = c.get("firstName", "").strip()
                    family = c.get("familyName", "").strip()
                    name = f"{first} {family}".strip() or c.get("name", "").strip() or email
                except Exception as e:
                    name = f"Error: {e}"
            
            print(f"  ID: {member_id}")
            print(f"  Name (mapped): {name}")
            print(f"  firstName: '{first}', familyName: '{family}'")
            print(f"  emailOrUserName: {email}")
            print()

if __name__ == "__main__":
    asyncio.run(test())

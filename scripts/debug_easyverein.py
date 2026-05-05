#!/usr/bin/env python3
"""
Debug script to inspect easyVerein API response structure.
Shows exactly what fields are returned for members and their contact details.
"""

import httpx
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.config import EASYVEREIN_API_KEY, EASYVEREIN_ORG_ID

EASYVEREIN_API_BASE = "https://easyverein.com/api/v2.0"


def get_auth_headers() -> dict:
    if not EASYVEREIN_API_KEY:
        print("ERROR: EASYVEREIN_API_KEY not set in config")
        sys.exit(1)
    return {
        "Authorization": f"Bearer {EASYVEREIN_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def fetch_members():
    headers = get_auth_headers()

    with httpx.Client(timeout=60.0) as client:
        # Build URL with optional org ID
        url = f"{EASYVEREIN_API_BASE}/member/"
        params = {"page_size": 10}  # Just fetch first 10 for debugging
        if EASYVEREIN_ORG_ID:
            params["organization"] = EASYVEREIN_ORG_ID

        print(f"Fetching members from: {url}")
        print(f"Params: {params}")
        print("-" * 60)

        response = client.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        # Handle both list and paginated response
        if isinstance(data, list):
            members = data
        elif isinstance(data, dict) and "results" in data:
            members = data["results"]
        else:
            members = []

        print(f"Total members fetched: {len(members)}")
        print("=" * 60)

        for i, member in enumerate(members[:5], 1):  # Show first 5
            print(f"\n--- Member {i} ---")
            print(f"Raw member fields: {list(member.keys())}")
            print(f"  membershipNumber: {member.get('membershipNumber')}")
            print(f"  emailOrUserName: {member.get('emailOrUserName')}")
            print(f"  _isApplication: {member.get('_isApplication')}")
            print(f"  joinDate: {member.get('joinDate')}")
            print(f"  resignationDate: {member.get('resignationDate')}")
            print(f"  _isBlocked: {member.get('_isBlocked')}")

            # Fetch contact details
            contact_url = member.get("contactDetails")
            if contact_url and isinstance(contact_url, str):
                print(f"\n  Fetching contact details from: {contact_url}")
                try:
                    contact_resp = client.get(contact_url, headers=headers)
                    contact_resp.raise_for_status()
                    contact = contact_resp.json()

                    print(f"  Contact fields: {list(contact.keys())}")
                    print(f"    name: '{contact.get('name', 'N/A')}'")
                    print(f"    firstName: '{contact.get('firstName', 'N/A')}'")
                    print(f"    familyName: '{contact.get('familyName', 'N/A')}'")
                    print(f"    email: '{contact.get('email', 'N/A')}'")
                    print(f"    privateEmail: '{contact.get('privateEmail', 'N/A')}'")
                    print(f"    companyEmail: '{contact.get('companyEmail', 'N/A')}'")
                    print(f"    mobilePhone: '{contact.get('mobilePhone', 'N/A')}'")
                    print(f"    phone: '{contact.get('phone', 'N/A')}'")

                    # Show what our mapping would produce
                    name = contact.get("name", "").strip()
                    if not name:
                        first = contact.get("firstName", "").strip()
                        family = contact.get("familyName", "").strip()
                        if first or family:
                            name = f"{first} {family}".strip()
                    if not name:
                        name = member.get("emailOrUserName", "").strip()

                    print(f"\n  --> Mapped name would be: '{name}'")

                except Exception as e:
                    print(f"  ERROR fetching contact details: {e}")
            else:
                print(f"  No contactDetails URL: {contact_url}")

            print("-" * 40)


if __name__ == "__main__":
    fetch_members()

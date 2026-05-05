#!/usr/bin/env python3
"""List all members with problematic data (email as name, missing email, etc.)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.members.db import SessionLocal
from backend.members.models import Mitglied


def list_problems():
    db = SessionLocal()
    try:
        # Find all members
        members = db.query(Mitglied).order_by(Mitglied.member_id).all()

        print(f"Total members in database: {len(members)}\n")
        print("=" * 70)

        # Category 1: Name looks like email
        email_as_name = []
        # Category 2: Name contains no space (single word)
        no_space_name = []
        # Category 3: Email looks like username (no @)
        username_as_email = []
        # Category 4: Missing email
        missing_email = []

        for m in members:
            # Check 1: Name contains @
            if m.name and "@" in m.name:
                email_as_name.append(m)
            # Check 2: No space in name (likely not "First Last")
            elif m.name and " " not in m.name:
                no_space_name.append(m)

            # Check 3: Email has no @ (is username)
            if m.email and "@" not in m.email:
                username_as_email.append(m)
            # Check 4: Missing email
            elif not m.email:
                missing_email.append(m)

        # Print results
        if email_as_name:
            print(f"\n🔴 NAME IS EMAIL ({len(email_as_name)} members):")
            print("-" * 70)
            for m in email_as_name:
                print(f"  ID {m.member_id:>5}: {m.name:<35} | Email: {m.email}")

        if no_space_name:
            print(f"\n🟡 SINGLE-WORD NAME ({len(no_space_name)} members):")
            print("-" * 70)
            for m in no_space_name:
                print(f"  ID {m.member_id:>5}: {m.name:<35} | Email: {m.email}")

        if username_as_email:
            print(f"\n🟠 EMAIL IS USERNAME ({len(username_as_email)} members):")
            print("-" * 70)
            for m in username_as_email:
                print(f"  ID {m.member_id:>5}: {m.name:<35} | Email: {m.email}")

        if missing_email:
            print(f"\n⚪ MISSING EMAIL ({len(missing_email)} members):")
            print("-" * 70)
            for m in missing_email:
                print(f"  ID {m.member_id:>5}: {m.name:<35} | Email: (none)")

        print("\n" + "=" * 70)
        total_problematic = len(
            set(
                m.member_id
                for m in (
                    email_as_name + no_space_name + username_as_email + missing_email
                )
            )
        )
        print(f"\nTotal members with issues: {total_problematic}")
        print(f"Total members OK: {len(members) - total_problematic}")

    finally:
        db.close()


if __name__ == "__main__":
    list_problems()

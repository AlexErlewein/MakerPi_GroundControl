#!/usr/bin/env python3
"""
Check database for members where name looks like an email address.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.members.db import SessionLocal
from backend.members.models import Mitglied


def check_email_names():
    db = SessionLocal()
    try:
        # Find members where name contains @ (email-like)
        members = db.query(Mitglied).filter(Mitglied.name.like('%@%')).all()
        
        print(f"Found {len(members)} members with email-like names:")
        print("=" * 60)
        
        for m in members:
            print(f"  member_id: {m.member_id}")
            print(f"  name:      {m.name}")
            print(f"  email:     {m.email}")
            print(f"  status:    {m.status}")
            print("-" * 40)
        
        # Also show some regular members for comparison
        print("\n\nSample of normal members (for comparison):")
        print("=" * 60)
        normal = db.query(Mitglied).filter(~Mitglied.name.like('%@%')).limit(5).all()
        for m in normal:
            print(f"  member_id: {m.member_id}")
            print(f"  name:      {m.name}")
            print(f"  email:     {m.email}")
            print("-" * 40)
            
    finally:
        db.close()


if __name__ == "__main__":
    check_email_names()

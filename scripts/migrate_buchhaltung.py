#!/usr/bin/env python3
"""Backfill existing paid Laufzettel into buchhaltung.db. Idempotent."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.laufzettel.db import SessionLocal as LZSession
from backend.laufzettel.models import Laufzettel, LaufzettelMaterial
from backend.buchhaltung.accounting import record_laufzettel_payment
from backend.buchhaltung.db import init_db, SessionLocal as BSession
from backend.buchhaltung.models import Verkauf

init_db()
lz_db = LZSession()
b_db = BSession()

already_recorded = {v.laufzettel_id for v in b_db.query(Verkauf).all()}
b_db.close()

paid = lz_db.query(Laufzettel).filter(Laufzettel.payment_method.isnot(None)).all()
count = 0
for lz in paid:
    if lz.id in already_recorded:
        continue
    materials = lz_db.query(LaufzettelMaterial).filter(LaufzettelMaterial.laufzettel_id == lz.id).all()
    record_laufzettel_payment(lz, materials)
    count += 1

lz_db.close()
print(f"Backfilled {count} Laufzettel ({len(paid) - count} already recorded)")

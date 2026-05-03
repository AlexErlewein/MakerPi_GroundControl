#!/usr/bin/env python3
"""
Test the sync logic with detailed error reporting.
Run from MakerPi_GroundControl directory.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Setup detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

try:
    from backend.members.easyverein import sync_members_from_easyverein
    logger.info("Starting sync test...")
    
    result = asyncio.run(sync_members_from_easyverein())
    
    logger.info("=" * 60)
    logger.info("SYNC RESULT:")
    logger.info(f"  success: {result['success']}")
    logger.info(f"  message: {result['message']}")
    logger.info(f"  created: {result['created']}")
    logger.info(f"  updated: {result['updated']}")
    logger.info(f"  errors:  {result['errors']}")
    logger.info("=" * 60)
    
except Exception as e:
    logger.exception("Sync failed with exception:")
    print(f"\nEXCEPTION: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

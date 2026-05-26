"""Shared SQLite startup utilities."""
import logging
import shutil
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def check_and_recover_engine(engine) -> bool:
    """Run quick_check on the DB backing this engine.

    If corrupt, moves the file to .corrupted and removes WAL/SHM so the
    caller's create_all() starts from a clean slate. Returns False when
    the DB was corrupt so the caller can log or alert.
    """
    db_path = engine.url.database
    if not db_path or db_path in (":memory:", ""):
        return True

    path = Path(db_path)
    if not path.exists():
        return True

    ok = False
    try:
        con = sqlite3.connect(str(path), timeout=5)
        try:
            rows = con.execute("PRAGMA quick_check").fetchmany(3)
            ok = bool(rows and rows[0][0] == "ok")
        finally:
            con.close()
    except Exception as e:
        logger.error("Integrity check failed for %s: %s", db_path, e)

    if not ok:
        dst = str(path) + ".corrupted"
        logger.error("Database %s is corrupt — moving to %s and recreating", db_path, dst)
        shutil.move(str(path), dst)
        for ext in ("-wal", "-shm"):
            sidecar = Path(str(path) + ext)
            if sidecar.exists():
                sidecar.unlink()

    return ok

#!/usr/bin/env python3
"""Check integrity of all GroundControl SQLite databases and auto-recover.

Designed to run as a cron job. If a database is corrupted, it attempts to
recover by dumping and reimporting. If recovery fails, the corrupted file
is renamed with a .corrupted suffix and GroundControl's init_db() will
create a fresh database on next startup.

Usage:
    python3 scripts/check_db_integrity.py          # check and auto-recover
    python3 scripts/check_db_integrity.py --check  # check only, no recovery
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# All SQLite databases used by GroundControl
PROJECT_ROOT = Path(__file__).parent.parent
DB_FILES = [
    PROJECT_ROOT / "auth.db",
    PROJECT_ROOT / "members.db",
    PROJECT_ROOT / "laufzettel.db",
    PROJECT_ROOT / "catalog.db",
    PROJECT_ROOT / "core.db",
    PROJECT_ROOT / "buchhaltung.db",
]

CHECK_ONLY = "--check" in sys.argv


def check_integrity(db_path: Path) -> bool:
    """Run PRAGMA integrity_check on a SQLite database."""
    result = subprocess.run(
        ["sqlite3", str(db_path), "PRAGMA integrity_check;"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout.strip()
    return output == "ok", output


def recover_db(db_path: Path) -> bool:
    """Attempt to recover a corrupted database by dump/reload."""
    fixed_path = db_path.with_suffix(".db.fixed")

    try:
        # Dump and reload into new file
        result = subprocess.run(
            f"sqlite3 '{db_path}' '.dump' | sqlite3 '{fixed_path}'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  Dump/reload failed: {result.stderr.strip()}")
            return False

        # Verify the recovered file
        ok, output = check_integrity(fixed_path)
        if not ok:
            print(f"  Recovered file still corrupt: {output}")
            fixed_path.unlink(missing_ok=True)
            return False

        # Replace corrupted with recovered
        backup_path = db_path.with_suffix(".db.corrupted")
        shutil.move(str(db_path), str(backup_path))
        shutil.move(str(fixed_path), str(db_path))
        print(f"  Recovered OK (corrupted backup: {backup_path.name})")
        return True
    except Exception as e:
        print(f"  Recovery error: {e}")
        fixed_path.unlink(missing_ok=True)
        return False


def main():
    had_errors = False

    for db_path in DB_FILES:
        if not db_path.exists():
            continue

        name = db_path.name
        ok, output = check_integrity(db_path)

        if ok:
            print(f"[OK] {name}")
            continue

        had_errors = True
        print(f"[CORRUPT] {name}: {output.splitlines()[0]}")

        if CHECK_ONLY:
            print(f"  (check-only mode, skipping recovery)")
            continue

        # Check if it's only index corruption (recoverable without data loss)
        if "index" in output.lower():
            print(f"  Attempting REINDEX...")
            result = subprocess.run(
                ["sqlite3", str(db_path), "REINDEX;"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                ok2, output2 = check_integrity(db_path)
                if ok2:
                    print(f"  REINDEX fixed it.")
                    continue
                print(f"  REINDEX didn't help: {output2}")

        # Full dump/reload recovery
        print(f"  Attempting dump/reload recovery...")
        if recover_db(db_path):
            continue

        # Last resort: rename corrupted file so init_db() creates a fresh one
        backup_path = db_path.with_suffix(".db.corrupted")
        if not backup_path.exists():
            shutil.move(str(db_path), str(backup_path))
            print(
                f"  Moved to {backup_path.name} — fresh DB will be created on startup"
            )
        else:
            print(f"  Backup already exists, removing corrupted file")
            db_path.unlink()

    sys.exit(1 if had_errors else 0)


if __name__ == "__main__":
    main()

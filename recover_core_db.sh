#!/bin/bash
# Recover corrupted core.db by reinitializing

set -e

cd /home/dev/Code/MakerPi_GroundControl

echo "🔍 Checking for Litestream backups..."
if [ -d ".core.db-litestream" ]; then
    echo "✅ Litestream backups found!"
    LATEST_BACKUP=$(ls -t .core.db-litestream/ | head -1)
    echo "📦 Latest backup: $LATEST_BACKUP"

    read -p "Restore from backup? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 Restoring from backup..."
        cp .core.db-litestream/$LATEST_BACKUP core.db
        echo "✅ Backup restored!"
        exit 0
    fi
fi

echo "⚠️  No usable backups found"
echo "🗑️  Will reinitialize core.db (MQTT messages and device data will be lost)"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted"
    exit 1
fi

# Backup corrupted database
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "💾 Backing up corrupted database..."
cp core.db core_corrupted_$TIMESTAMP.db

# Remove corrupted database
echo "🗑️  Removing corrupted core.db..."
rm core.db core.db-shm core.db-wal 2>/dev/null || true

# Reinitialize database by starting the app briefly
echo "🔧 Reinitializing database..."
source .venv/bin/activate
timeout 10 python3 -c "
from backend.core.db import init_db
init_db()
print('Database initialized successfully')
" || echo "Init completed"

# Run migration
echo "🗄️  Running 3VL migration..."
python3 migrate_add_3vl_columns.py

echo "✅ Recovery complete!"
echo ""
echo "📊 New database created. Run 'sudo systemctl start groundcontrol' to start the service."
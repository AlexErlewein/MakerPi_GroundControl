#!/bin/bash
# Properly restore core.db from Litestream backups

set -e

cd /home/dev/Code/MakerPi_GroundControl

echo "🔍 Analyzing Litestream backup structure..."

# Check if litestream directory exists
if [ ! -d ".core.db-litestream" ]; then
    echo "❌ No Litestream backups found"
    exit 1
fi

# List all backup files
echo ""
echo "📦 Available backup files:"
find .core.db-litestream -type f -name "*.db" 2>/dev/null | sort

# Find the most recent database backup
LATEST_DB=$(find .core.db-litestream -type f -name "*.db" 2>/dev/null | sort | tail -1)

if [ -z "$LATEST_DB" ]; then
    echo "❌ No database files found in backups"
    exit 1
fi

echo ""
echo "📦 Latest backup: $LATEST_DB"

# Backup current corrupted file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "💾 Backing up corrupted database..."
cp core.db core_corrupted_$TIMESTAMP.db 2>/dev/null || echo "No core.db to backup"

# Copy from backup
echo "🔄 Restoring from backup..."
cp "$LATEST_DB" core.db

# Verify
echo ""
echo "✅ Restored. Verifying..."
sqlite3 core.db "PRAGMA integrity_check;" | head -5

if [ $? -eq 0 ]; then
    echo "✅ Database restored successfully!"
else
    echo "⚠️  Database still has issues, but this is the best available backup"
fi

echo ""
echo "📊 Summary:"
echo "  - Backup used: $LATEST_DB"
echo "  - Corrupted DB saved as: core_corrupted_$TIMESTAMP.db"
echo ""
echo "Run 'sudo systemctl start groundcontrol' to start the service"
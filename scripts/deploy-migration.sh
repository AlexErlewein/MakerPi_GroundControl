#!/bin/bash
# Deploy and run database migration on Pi

set -e

echo "🚀 Deploying migration script to Pi..."

# Load connection info
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config/config.json" 2>/dev/null || true

# Fallback to defaults if config doesn't load
PI_HOST="${pi_host:-h3ckepi.local}"
PI_USER="${pi_user:-pi}"
PROJECT_DIR="${project_dir:-/home/dev/Code/MakerPi_GroundControl}"

echo "📡 Target: $PI_USER@$PI_HOST:$PROJECT_DIR"

# Copy migration script
echo "📤 Copying migration script..."
scp "$SCRIPT_DIR/migrate_add_3vl_columns.py" "$PI_USER@$PI_HOST:$PROJECT_DIR/"

# Run migration
echo "🔧 Running migration on Pi..."
ssh "$PI_USER@$PI_HOST" "cd '$PROJECT_DIR' && python3 migrate_add_3vl_columns.py"

# Restart the service
echo "🔄 Restarting GroundControl service..."
ssh "$PI_USER@$PI_HOST" "sudo systemctl restart groundcontrol"

echo "✅ Deployment complete!"
echo "📊 Check status with: ssh $PI_USER@$PI_HOST 'sudo systemctl status groundcontrol -l'"
echo "📝 View logs with: ssh $PI_USER@$PI_HOST 'sudo journalctl -u groundcontrol -f'"
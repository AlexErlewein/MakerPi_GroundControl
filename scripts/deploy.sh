#!/bin/bash
# Deploy script to sync files to the Pi and restart the service
# Usage: ./scripts/deploy.sh <pi-hostname-or-ip> [--update-deps]

PI_HOST=${1:-"raspberrypi.local"}
UPDATE_DEPS=${2:-""}
PI_USER="pi"
PROJECT_DIR="/opt/makerpi-groundcontrol"

echo "🚀 Deploying to $PI_HOST..."

# Sync files to Pi
echo "Syncing files..."
rsync -av --progress \
    --exclude='venv/' \
    --exclude='*.db' \
    --exclude='__pycache__/' \
    --exclude='.git/' \
    --exclude='.gitignore' \
    ./ $PI_USER@$PI_HOST:$PROJECT_DIR/

# Update dependencies if requested
if [ "$UPDATE_DEPS" = "--update-deps" ]; then
    echo "Updating Python dependencies..."
    ssh $PI_USER@$PI_HOST "cd $PROJECT_DIR && source venv/bin/activate && if command -v uv &> /dev/null; then uv pip install -r requirements.txt; else pip install -r requirements.txt; fi"
fi

# Restart service on Pi
echo "Restarting GroundControl service..."
ssh $PI_USER@$PI_HOST "sudo systemctl restart groundcontrol"

# Check status
echo "Checking service status..."
ssh $PI_USER@$PI_HOST "sudo systemctl status groundcontrol --no-pager -l | grep -E '(Active:|Main PID)'"

echo ""
echo "✅ Deploy complete!"
echo "Dashboard: http://$PI_HOST:8000"

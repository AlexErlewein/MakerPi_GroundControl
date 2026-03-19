#!/bin/bash
# Deploy script to sync files to the Pi and restart the service
# Usage: ./scripts/deploy.sh <pi-hostname-or-ip> [--update-deps]

PI_HOST=${1:-"192.168.178.47"}
UPDATE_DEPS=${2:-""}
PI_USER="alex"
PROJECT_DIR="home/alex/MakerPi_GroundControl"

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
    ssh $PI_USER@$PI_HOST "cd $PROJECT_DIR && if command -v uv &> /dev/null; then uv sync; else source venv/bin/activate && pip install -r requirements.txt; fi"
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

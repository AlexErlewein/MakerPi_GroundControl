#!/bin/bash
# Deploy script to sync files to the Pi and restart the service
# Usage: ./scripts/deploy.sh [--update-deps]
# Configuration: Edit config.json in the project root

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/config.json"

if [ -f "$CONFIG_FILE" ] && command -v jq &> /dev/null; then
    PI_HOST=$(jq -r '.pi_host // "192.168.178.47"' "$CONFIG_FILE")
    TAILSCALE_IP=$(jq -r '.tailscale_ip // empty' "$CONFIG_FILE")
    PI_USER=$(jq -r '.pi_user // "alex"' "$CONFIG_FILE")
    PROJECT_DIR=$(jq -r '.project_dir // "home/alex/MakerPi_GroundControl"' "$CONFIG_FILE")
else
    PI_HOST=${1:-"192.168.178.47"}
    TAILSCALE_IP=""
    PI_USER="alex"
    PROJECT_DIR="home/alex/MakerPi_GroundControl"
fi

# Try Tailscale IP first if available, fallback to local PI_HOST
if [ -n "$TAILSCALE_IP" ]; then
    echo "🔍 Testing Tailscale connection ($TAILSCALE_IP)..."
    # Test with visible output and longer timeout (10s)
    if ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new "$PI_USER@$TAILSCALE_IP" "echo 'tailscale-ok'" 2>&1 | grep -q "tailscale-ok"; then
        echo "✅ Tailscale connection successful"
        PI_HOST="$TAILSCALE_IP"
    else
        echo "⚠️ Tailscale connection failed, falling back to local IP ($PI_HOST)..."
    fi
fi

UPDATE_DEPS=${2:-""}

echo "🚀 Deploying to $PI_USER@$PI_HOST..."

# Sync files to Pi
echo "Syncing files..."
rsync -av --progress \
    --exclude='venv/' \
    --exclude='.venv/' \
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

#!/bin/bash
# ============================================================================
# Plane Deploy Script for MakerPi GroundControl
# Deploys modern project management tool
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/config.json"

if [ -f "$CONFIG_FILE" ] && command -v jq &> /dev/null; then
    TAILSCALE_IP=$(jq -r '.tailscale_ip // "100.78.55.14"' "$CONFIG_FILE")
    PI_USER=$(jq -r '.pi_user // "dev"' "$CONFIG_FILE")
else
    TAILSCALE_IP="100.78.55.14"
    PI_USER="dev"
fi

echo "🚀 Deploying Plane to $PI_USER@$TAILSCALE_IP..."

# Create remote directory
ssh "$PI_USER@$TAILSCALE_IP" "mkdir -p ~/plane"

# Copy files
echo "📤 Copying docker-compose.yml..."
scp "$SCRIPT_DIR/docker-compose.yml" "$PI_USER@$TAILSCALE_IP:~/plane/"

# Generate secret key if not exists
ssh "$PI_USER@$TAILSCALE_IP" "
    if [ ! -f ~/plane/.env ]; then
        echo 'SECRET_KEY='\$(openssl rand -hex 32) > ~/plane/.env
        echo '🔑 Generated SECRET_KEY'
    fi
"

# Start Plane
echo "🐳 Starting Plane (this may take a few minutes on first run)..."
ssh "$PI_USER@$TAILSCALE_IP" "cd ~/plane && docker compose pull && docker compose up -d"

echo ""
echo "✅ Plane deployed!"
echo ""
echo "⏳ Plane will take 2-5 minutes to initialize on first startup."
echo ""
echo "Access URLs:"
echo "  http://$TAILSCALE_IP:3001    (Tailscale)"
echo "  http://192.168.3.228:3001     (Local network)"
echo ""
echo "First time setup:"
echo "1. Wait for services to start"
echo "2. Open the URL above"
echo "3. Create your workspace and project"
echo ""
echo "View logs: ssh $PI_USER@$TAILSCALE_IP 'docker logs -f plane-api'"

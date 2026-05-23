#!/bin/bash
# Sync OAuth config files to Raspberry Pi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/config.json"

if [ -f "$CONFIG_FILE" ] && command -v jq &> /dev/null; then
    PI_HOST=$(jq -r '.pi_host // "192.168.178.47"' "$CONFIG_FILE")
    TAILSCALE_IP=$(jq -r '.tailscale_ip // empty' "$CONFIG_FILE")
    PI_USER=$(jq -r '.pi_user // "alex"' "$CONFIG_FILE")
    PROJECT_DIR=$(jq -r '.project_dir // "/home/alex/MakerPi_GroundControl"' "$CONFIG_FILE")
else
    PI_HOST="192.168.178.47"
    TAILSCALE_IP=""
    PI_USER="alex"
    PROJECT_DIR="/home/alex/MakerPi_GroundControl"
fi

# Resolve server IP
if [ -n "$TAILSCALE_IP" ]; then
    echo "🔍 Testing Tailscale connection ($TAILSCALE_IP)..."
    if ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new \
        "$PI_USER@$TAILSCALE_IP" "echo tailscale-ok" 2>&1 | grep -q "tailscale-ok"; then
        echo "✅ Tailscale OK"
        PI_HOST="$TAILSCALE_IP"
    else
        echo "⚠️  Tailscale failed, using local IP ($PI_HOST)..."
    fi
fi

echo "🚀 Syncing OAuth config files to $PI_USER@$PI_HOST..."
echo ""

# Files to sync
FILES=(
    "config/config.json"
    "config/gmail_oauth_token.json"
    "config/gmail_oauth_client_secrets.json"
    "config/gdrive_token.json"
    "config/gdrive_client_secrets.json"
)

# Sync each file
for FILE in "${FILES[@]}"; do
    LOCAL_PATH="$PROJECT_ROOT/$FILE"
    REMOTE_PATH="$PROJECT_DIR/$FILE"

    if [ ! -f "$LOCAL_PATH" ]; then
        echo "⚠️  Skipping $FILE (not found)"
        continue
    fi

    echo "📄 Syncing $FILE..."
    scp -o StrictHostKeyChecking=accept-new "$LOCAL_PATH" "$PI_USER@$PI_HOST:$REMOTE_PATH"
    if [ $? -eq 0 ]; then
        echo "   ✅ $FILE synced"
    else
        echo "   ❌ Failed to sync $FILE"
        exit 1
    fi
done

echo ""
echo "✅ OAuth config files synced successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Deploy the code changes:"
echo "      ./scripts/deploy.sh --update-deps"
echo "   2. The service will restart automatically"
echo "   3. Check logs: ssh $PI_USER@$PI_HOST 'sudo journalctl -u groundcontrol -f'"
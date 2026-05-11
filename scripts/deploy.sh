#!/bin/bash
# Deploy script – git-based: commit & push locally, then git pull on server.
# Usage:
#   ./scripts/deploy.sh                  – deploy (prompts for commit message if needed)
#   ./scripts/deploy.sh --migrate        – deploy + run DB migration on server
#   ./scripts/deploy.sh --update-deps    – deploy + pip install on server

set -e

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

RUN_MIGRATE=0
UPDATE_DEPS=0
for arg in "$@"; do
    [ "$arg" = "--migrate" ]      && RUN_MIGRATE=1
    [ "$arg" = "--update-deps" ]  && UPDATE_DEPS=1
done

# ── 1. Commit & push locally ───────────────────────────────────────────────
cd "$PROJECT_ROOT"

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "📝 Uncommitted changes found:"
    git status --short
    echo ""
    read -r -p "Commit message (leave empty to abort): " MSG
    if [ -z "$MSG" ]; then
        echo "❌ Aborted – nothing committed."
        exit 1
    fi
    git add -A
    git commit -m "$MSG"
fi

echo "⬆️  Pushing to origin..."
git push

# ── 2. Resolve server IP ───────────────────────────────────────────────────
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

echo "🚀 Deploying to $PI_USER@$PI_HOST..."

# ── 3. Pull on server (hard reset to origin – no merge conflicts) ──────────
ssh "$PI_USER@$PI_HOST" "
    set -e
    cd $PROJECT_DIR
    git fetch origin
    git reset --hard origin/\$(git rev-parse --abbrev-ref HEAD)
    echo '✅ Server is at:' \$(git log -1 --oneline)
"

# ── 4. Optional: DB migration ─────────────────────────────────────────────
if [ "$RUN_MIGRATE" = "1" ]; then
    echo "🗄️  Running DB migration..."
    ssh "$PI_USER@$PI_HOST" "cd $PROJECT_DIR && .venv/bin/python scripts/migrate_payment_fields.py"
fi

# ── 5. Optional: update Python deps ───────────────────────────────────────
if [ "$UPDATE_DEPS" = "1" ]; then
    echo "📦 Updating Python dependencies..."
    ssh "$PI_USER@$PI_HOST" "cd $PROJECT_DIR && if command -v uv &>/dev/null; then uv sync; else .venv/bin/pip install -r requirements.txt; fi"
fi

# ── 6. Restart service ────────────────────────────────────────────────────
echo "🔄 Restarting GroundControl service..."
ssh -t "$PI_USER@$PI_HOST" "sudo systemctl restart groundcontrol && sleep 2 && \
    sudo systemctl status groundcontrol --no-pager -l | grep -E '(Active:|Main PID)'"

# ── 7. Deploy Planka files (if planka directory exists) ─────────────────────
PLANKA_DIR="$PROJECT_ROOT/planka"
PLANKA_REMOTE_DIR="/home/$PI_USER/planka"

if [ -d "$PLANKA_DIR" ] && [ -f "$PLANKA_DIR/custom.css" ]; then
    echo ""
    echo "🎨 Checking Planka files..."
    
    # Check if remote planka directory exists, create if not
    ssh "$PI_USER@$PI_HOST" "mkdir -p $PLANKA_REMOTE_DIR"
    
    # Compare files and only copy if different
    CSS_CHANGED=0
    COMPOSE_CHANGED=0
    
    # Check custom.css
    LOCAL_CSS_MD5=$(md5sum "$PLANKA_DIR/custom.css" 2>/dev/null | awk '{print $1}')
    REMOTE_CSS_MD5=$(ssh "$PI_USER@$PI_HOST" "md5sum $PLANKA_REMOTE_DIR/custom.css 2>/dev/null | awk '{print \$1}'" || echo "")
    
    if [ "$LOCAL_CSS_MD5" != "$REMOTE_CSS_MD5" ]; then
        echo "  📤 custom.css changed – copying..."
        scp "$PLANKA_DIR/custom.css" "$PI_USER@$PI_HOST:$PLANKA_REMOTE_DIR/custom.css"
        CSS_CHANGED=1
    else
        echo "  ✓ custom.css unchanged"
    fi
    
    # Check docker-compose.yml
    if [ -f "$PLANKA_DIR/docker-compose.yml" ]; then
        LOCAL_COMPOSE_MD5=$(md5sum "$PLANKA_DIR/docker-compose.yml" 2>/dev/null | awk '{print $1}')
        REMOTE_COMPOSE_MD5=$(ssh "$PI_USER@$PI_HOST" "md5sum $PLANKA_REMOTE_DIR/docker-compose.yml 2>/dev/null | awk '{print \$1}'" || echo "")
        
        if [ "$LOCAL_COMPOSE_MD5" != "$REMOTE_COMPOSE_MD5" ]; then
            echo "  📤 docker-compose.yml changed – copying..."
            scp "$PLANKA_DIR/docker-compose.yml" "$PI_USER@$PI_HOST:$PLANKA_REMOTE_DIR/docker-compose.yml"
            COMPOSE_CHANGED=1
        else
            echo "  ✓ docker-compose.yml unchanged"
        fi
    fi
    
    # Restart Planka if any files changed
    if [ "$CSS_CHANGED" = "1" ] || [ "$COMPOSE_CHANGED" = "1" ]; then
        echo "  🔄 Restarting Planka..."
        ssh "$PI_USER@$PI_HOST" "cd $PLANKA_REMOTE_DIR && docker compose restart planka 2>/dev/null || docker compose up -d"
        echo "  ✅ Planka restarted"
    else
        echo "  ✓ Planka unchanged – no restart needed"
    fi
fi

echo ""
echo "✅ Deploy complete!"
echo "Dashboard: http://$PI_HOST:8000"
echo "Kanban:    http://$PI_HOST:3001"

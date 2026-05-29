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
    ssh "$PI_USER@$PI_HOST" "
        set -e
        cd $PROJECT_DIR

        # Ensure uv is installed
        if ! command -v uv &>/dev/null; then
            echo 'uv not found, installing...'
            curl -LsSf https://astral.sh/uv/install.sh | sh
            export PATH=\"\$HOME/.local/bin:\$PATH\"
        fi

        echo 'Syncing dependencies with uv...'
        uv sync
    "
fi

# ── 6. Stop service, checkpoint WAL files, then start ────────────────────
echo "⏹️  Stopping GroundControl services..."
ssh "$PI_USER@$PI_HOST" "sudo systemctl stop groundcontrol && sudo systemctl stop groundcontrol-docs"

echo "💾 Checkpointing WAL files..."
ssh "$PI_USER@$PI_HOST" "
    cd $PROJECT_DIR
    for db in auth.db core.db members.db laufzettel.db catalog.db buchhaltung.db push.db; do
        if [ -f \"\$db\" ]; then
            sqlite3 \"\$db\" 'PRAGMA wal_checkpoint(TRUNCATE);' 2>/dev/null && echo \"  ✓ \$db\" || echo \"  ⚠ \$db (checkpoint failed)\"
        fi
    done
"

echo "▶️  Starting GroundControl services..."
ssh -t "$PI_USER@$PI_HOST" "
    sudo systemctl start groundcontrol && sudo systemctl start groundcontrol-docs && sleep 2 && \
    sudo systemctl status groundcontrol groundcontrol-docs --no-pager -l | grep -E '(Active:|Main PID)'
"

echo ""
echo "✅ Deploy complete!"
echo "Dashboard: https://$PI_HOST:8443"
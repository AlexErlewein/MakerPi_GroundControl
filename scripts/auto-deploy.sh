#!/bin/bash
# Auto-deploy: pulls latest main branch and restarts services if anything changed.
# Runs as the service user via a systemd timer (see install-autodeploy.sh).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

log() { echo "[auto-deploy] $(date -Iseconds) $*"; }

# Fetch without touching the working tree
if ! git fetch origin main --quiet 2>&1; then
    log "ERROR: git fetch failed (no network?). Skipping."
    exit 1
fi

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "Up to date ($(git rev-parse --short HEAD))"
    exit 0
fi

log "New commits: $(git rev-parse --short "$LOCAL") -> $(git rev-parse --short "$REMOTE")"
log "Changes:"
git log --oneline "$LOCAL..$REMOTE"

# Pull — ff-only keeps us safe; if someone force-pushed or branches diverged
# this exits non-zero and the timer retries next cycle instead of clobbering.
git pull --ff-only origin main

# Update Python dependencies only when pyproject.toml changed
if git diff --name-only "$LOCAL" HEAD | grep -q "^pyproject.toml$"; then
    log "pyproject.toml changed — updating dependencies..."
    if command -v uv &>/dev/null; then
        uv sync
    elif [ -f "$PROJECT_DIR/venv/bin/pip" ]; then
        "$PROJECT_DIR/venv/bin/pip" install -e . --quiet
    else
        log "WARNING: Neither uv nor venv found — skipping dependency update."
    fi
fi

log "Restarting services..."
sudo systemctl restart groundcontrol groundcontrol-docs

log "Deploy complete. Now running: $(git rev-parse --short HEAD)"

#!/bin/bash
# Installs the auto-deploy systemd timer on the Raspberry Pi.
# Run once with: sudo bash scripts/install-autodeploy.sh
#
# What this does:
#   1. Grants the service user passwordless sudo to restart the two services
#   2. Installs a systemd one-shot service that runs auto-deploy.sh
#   3. Installs a systemd timer that triggers it every 5 minutes
#
# Prerequisites: The Pi must be able to reach GitHub via git fetch without
# interactive credentials. For a public repo over HTTPS this works out of
# the box. For a private repo, set up an SSH deploy key first:
#   https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys

set -e

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root:  sudo bash scripts/install-autodeploy.sh"
    exit 1
fi

SERVICE_USER=${SUDO_USER:-$USER}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Installing auto-deploy timer"
echo "  User:        $SERVICE_USER"
echo "  Project dir: $PROJECT_DIR"
echo ""

# ── 1. Make the deploy script executable ──────────────────────────────────────
chmod +x "$PROJECT_DIR/scripts/auto-deploy.sh"

# ── 2. Passwordless sudo for restarting all GroundControl services ────────────
SUDOERS_FILE="/etc/sudoers.d/groundcontrol-deploy"
cat > "$SUDOERS_FILE" << EOF
# Allow $SERVICE_USER to restart GroundControl services (used by auto-deploy)
$SERVICE_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart groundcontrol
$SERVICE_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart groundcontrol-docs
$SERVICE_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart zigbee2mqtt
$SERVICE_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart sqlite-web
EOF
chmod 440 "$SUDOERS_FILE"
echo "Sudoers rule written: $SUDOERS_FILE"

# ── 3. Systemd one-shot service ───────────────────────────────────────────────
cat > /etc/systemd/system/groundcontrol-autodeploy.service << EOF
[Unit]
Description=MakerPi GroundControl Auto-Deploy
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/auto-deploy.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=groundcontrol-autodeploy
EOF

# ── 4. Systemd timer (every 5 minutes) ───────────────────────────────────────
cat > /etc/systemd/system/groundcontrol-autodeploy.timer << EOF
[Unit]
Description=Check for MakerPi GroundControl updates every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF

# ── 5. Enable and start ───────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable groundcontrol-autodeploy.timer
systemctl start groundcontrol-autodeploy.timer

echo ""
echo "Done! Auto-deploy timer is active."
echo ""
echo "The Pi now checks GitHub every 5 minutes and redeploys on changes to main."
echo ""
echo "Useful commands:"
echo "  Watch deploy logs:      sudo journalctl -u groundcontrol-autodeploy -f"
echo "  Trigger manual deploy:  sudo systemctl start groundcontrol-autodeploy.service"
echo "  Check timer status:     systemctl status groundcontrol-autodeploy.timer"
echo "  Disable auto-deploy:    sudo systemctl disable --now groundcontrol-autodeploy.timer"

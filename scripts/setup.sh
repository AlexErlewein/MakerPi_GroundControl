#!/bin/bash
# MakerPi GroundControl - Setup Script for Raspberry Pi
# Run this on your Pi: sudo bash setup.sh
#
# Installs:
#   - uv (fast Python package manager)
#   - Mosquitto MQTT broker
#   - MakerPi GroundControl FastAPI backend
#   - SQLite WAL mode + DB integrity cron job

set -e

echo "🛰️  MakerPi GroundControl Setup"
echo "================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update system
echo -e "${YELLOW}Updating system packages...${NC}"
apt update && apt upgrade -y

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
apt install -y \
    python3 \
    python3-pip \
    mosquitto \
    mosquitto-clients \
    sqlite3 \
    git \
    curl \
    jq \
    docker.io || true

SERVICE_USER=${SUDO_USER:-$USER}
PROJECT_DIR="$(eval echo ~$SERVICE_USER)/Code/MakerPi_GroundControl"

# ── uv (fast Python package manager) ─────────────────────────────────────────
UV_BIN="/home/$SERVICE_USER/.local/bin/uv"
SERVICE_HOME="/home/$SERVICE_USER"

echo -e "${YELLOW}Installing uv package manager...${NC}"
if [ ! -f "$UV_BIN" ]; then
    su - "$SERVICE_USER" -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "✅ uv installed"
else
    echo "✅ uv already installed"
fi

# ── Mosquitto MQTT Broker ─────────────────────────────────────────────────────
echo -e "${YELLOW}Configuring Mosquitto broker...${NC}"
cat > /etc/mosquitto/mosquitto.conf << MOSQEOF
listener 1883
allow_anonymous true
persistence true
persistence_location /var/lib/mosquitto/
log_dest file /var/log/mosquitto/mosquitto.log
MOSQEOF

mkdir -p /var/lib/mosquitto /var/log/mosquitto
chown mosquitto:mosquitto /var/lib/mosquitto /var/log/mosquitto

# ── Python Dependencies ────────────────────────────────────────────────────────
echo -e "${YELLOW}Installing Python packages with uv...${NC}"
su - "$SERVICE_USER" -c "cd $PROJECT_DIR && $UV_BIN sync"

# ── config.json ────────────────────────────────────────────────────────────────
echo -e "${YELLOW}Setting up config.json...${NC}"
if [ ! -f "$PROJECT_DIR/config/config.json" ]; then
    if [ -f "$PROJECT_DIR/config/config.json.example" ]; then
        cp "$PROJECT_DIR/config/config.json.example" "$PROJECT_DIR/config/config.json"
        echo "✅ config.json created from example"
        echo "⚠️  Edit config/config.json to add your secrets and credentials"
    else
        echo "⚠️  config.json.example not found, creating minimal config.json"
        cat > "$PROJECT_DIR/config/config.json" << EOF
{
    "pi_host": "$(hostname -I | awk '{print $1}')",
    "pi_user": "$SERVICE_USER",
    "project_dir": "$PROJECT_DIR",
    "mqtt_broker": "localhost",
    "mqtt_port": 1883,
    "secret_key": "change-me-to-a-random-secret",
    "admin_username": "admin",
    "admin_password": "changeme"
}
EOF
    fi
else
    echo "✅ config.json already exists"
fi
# Ensure the service user owns the config directory so the app can write settings at runtime
chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR/config/"

# ── Systemd Services ─────────────────────────────────────────────────────────
echo -e "${YELLOW}Creating systemd services...${NC}"

# Main app service (port 8000)
cat > /etc/systemd/system/groundcontrol.service << EOF
[Unit]
Description=MakerPi GroundControl Web Service
After=network.target mosquitto.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
Environment="PATH=$SERVICE_HOME/.local/bin"

[Install]
WantedBy=multi-user.target
EOF

# Docs service (port 8001)
cat > /etc/systemd/system/groundcontrol-docs.service << EOF
[Unit]
Description=MakerPi GroundControl Docs Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/uvicorn backend.docs_app:app --host 0.0.0.0 --port 8001 --root-path /docs
Restart=always
RestartSec=10
Environment="PATH=$SERVICE_HOME/.local/bin"

[Install]
WantedBy=multi-user.target
EOF

# ── Remove legacy Docker issue trackers ──────────────────────────────────────
echo -e "${YELLOW}Checking for legacy issue tracker installations...${NC}"
REMOVED_SOMETHING=false

# Stop and remove YouTrack container
if command -v docker &> /dev/null && docker ps -a --format '{{.Names}}' | grep -q 'youtrack-server'; then
    echo "  Removing YouTrack container..."
    docker stop youtrack-server 2>/dev/null || true
    docker rm youtrack-server 2>/dev/null || true
    REMOVED_SOMETHING=true
fi

# Remove Plane containers (various naming schemes)
if command -v docker &> /dev/null; then
    for container in plane-web plane-api plane-worker plane-beat-worker plane-proxy plane-db plane-redis plane-mq plane-minio plane-space plane-admin; do
        if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
            echo "  Removing Plane container: $container"
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
            REMOVED_SOMETHING=true
        fi
    done
fi

# Remove data directories
for dir in /opt/plane /opt/youtrack; do
    if [ -d "$dir" ]; then
        echo "  Removing $dir..."
        rm -rf "$dir"
        REMOVED_SOMETHING=true
    fi
done

if [ "$REMOVED_SOMETHING" = true ]; then
    echo "  ✅ Legacy issue trackers cleaned up (moved to cloud-hosted)"
else
    echo "  ✅ No legacy installations found"
fi

# ── DB Integrity Cron Job ─────────────────────────────────────────────────────
echo -e "${YELLOW}Setting up DB integrity monitoring cron job...${NC}"
CRON_CMD="0 * * * * $PROJECT_DIR/.venv/bin/python $PROJECT_DIR/scripts/check_db_integrity.py >> /var/log/gc-db-check.log 2>&1"

# Add to crontab if not already present
su - "$SERVICE_USER" -c "crontab -l 2>/dev/null | grep -q 'check_db_integrity.py' || (crontab -l 2>/dev/null; echo \"$CRON_CMD\") | crontab -"
echo "✅ Cron job added (hourly integrity checks logged to /var/log/gc-db-check.log)"

# ── Enable and start all services ─────────────────────────────────────────────
echo -e "${YELLOW}Enabling and starting services...${NC}"
systemctl daemon-reload
systemctl enable mosquitto
systemctl restart mosquitto
systemctl enable groundcontrol
systemctl start groundcontrol
systemctl enable groundcontrol-docs
systemctl start groundcontrol-docs

# Wait for services to start
sleep 5

# Check status
echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Service Status:"
echo "---------------"
systemctl status mosquitto --no-pager -l | grep -E "(Active:|loaded)" || echo "Mosquitto: running"
echo ""
systemctl status groundcontrol --no-pager -l | grep -E "(Active:|Main PID)" || echo "GroundControl: running"
echo ""
systemctl status groundcontrol-docs --no-pager -l | grep -E "(Active:|Main PID)" || echo "Docs: running"
echo ""
echo -e "${GREEN}Access your dashboard at:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo -e "${GREEN}Access your docs site at:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):8001"
echo ""
echo "MQTT Broker:"
echo "  Host: $(hostname -I | awk '{print $1}')"
echo "  Port: 1883"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u groundcontrol -f"
echo "  sudo journalctl -u groundcontrol-docs -f"
echo "  sudo journalctl -u mosquitto -f"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Edit config/config.json to add your secrets (SumUp, easyVerein, etc.)"
echo "  2. Restart: sudo systemctl restart groundcontrol"
echo ""
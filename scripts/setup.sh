#!/bin/bash
# MakerPi GroundControl - Setup Script for Raspberry Pi
# Run this on your Pi: sudo bash setup.sh
#
# Installs:
#   - uv (fast Python package manager)
#   - Mosquitto MQTT broker
#   - MakerPi GroundControl FastAPI backend
#   - Zigbee2MQTT (requires a Zigbee USB dongle)
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
    nodejs \
    npm \
    git \
    curl \
    jq

SERVICE_USER=${SUDO_USER:-$USER}
PROJECT_DIR="$(eval echo ~$SERVICE_USER)/Code/MakerPi_GroundControl"

# ── uv (fast Python package manager) ─────────────────────────────────────────
echo -e "${YELLOW}Installing uv package manager...${NC}"
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Make sure the PATH includes ~/.local/bin for the current shell
    export PATH="$HOME/.local/bin:$PATH"
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
su - "$SERVICE_USER" -c "cd $PROJECT_DIR && $HOME/.local/bin/uv sync"

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
ExecStart=$HOME/.local/bin/uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
Environment="PATH=$HOME/.local/bin"

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
ExecStart=$HOME/.local/bin/uv run uvicorn backend.docs_app:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10
Environment="PATH=$HOME/.local/bin"

[Install]
WantedBy=multi-user.target
EOF

# ── Zigbee2MQTT ────────────────────────────────────────────────────────────────
echo -e "${YELLOW}Installing Zigbee2MQTT...${NC}"

Z2M_DIR="/opt/zigbee2mqtt"

if [ -d "$Z2M_DIR" ]; then
    echo "Zigbee2MQTT already cloned, pulling latest..."
    git -C "$Z2M_DIR" pull
else
    git clone --depth 1 https://github.com/Koenkk/zigbee2mqtt.git "$Z2M_DIR"
fi

npm install -g pnpm
rm -rf "$Z2M_DIR/node_modules"
CI=true pnpm --dir "$Z2M_DIR" install

mkdir -p "$Z2M_DIR/data"

if [ ! -f "$Z2M_DIR/data/configuration.yaml" ]; then
    cp "$PROJECT_DIR/config/zigbee2mqtt.yaml" "$Z2M_DIR/data/configuration.yaml"
    echo "Zigbee2MQTT config copied to $Z2M_DIR/data/configuration.yaml"
else
    echo "Existing Zigbee2MQTT config found, skipping copy."
fi

chown -R "$SERVICE_USER":"$SERVICE_USER" "$Z2M_DIR"
usermod -aG dialout "$SERVICE_USER"
echo "Added $SERVICE_USER to dialout group (serial port access)"

cat > /etc/systemd/system/zigbee2mqtt.service << EOF
[Unit]
Description=Zigbee2MQTT
After=network.target mosquitto.service
Wants=mosquitto.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$Z2M_DIR
ExecStart=node $Z2M_DIR/index.js
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ── DB Integrity Cron Job ─────────────────────────────────────────────────────
echo -e "${YELLOW}Setting up DB integrity monitoring cron job...${NC}"
CRON_CMD="0 * * * * $HOME/.local/bin/uv run $PROJECT_DIR/scripts/check_db_integrity.py >> /var/log/gc-db-check.log 2>&1"

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
systemctl enable zigbee2mqtt
systemctl start zigbee2mqtt

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
systemctl status zigbee2mqtt --no-pager -l | grep -E "(Active:|Main PID)" || echo "Zigbee2MQTT: running"
echo ""
echo -e "${GREEN}Access your dashboard at:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo -e "${GREEN}Access your docs site at:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):8001"
echo ""
echo -e "${GREEN}Zigbee2MQTT frontend at:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):8090"
echo ""
echo "MQTT Broker:"
echo "  Host: $(hostname -I | awk '{print $1}')"
echo "  Port: 1883"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u groundcontrol -f"
echo "  sudo journalctl -u groundcontrol-docs -f"
echo "  sudo journalctl -u mosquitto -f"
echo "  sudo journalctl -u zigbee2mqtt -f"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Edit config/config.json to add your secrets (SumUp, easyVerein, etc.)"
echo "  2. If using Zigbee2MQTT: plug in your USB dongle and edit /opt/zigbee2mqtt/data/configuration.yaml"
echo "  3. Run: sudo systemctl restart zigbee2mqtt"
echo ""
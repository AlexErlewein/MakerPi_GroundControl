#!/bin/bash
# MakerPi GroundControl - Setup Script for Raspberry Pi
# Run this on your Pi: sudo bash setup.sh
#
# Installs:
#   - Mosquitto MQTT broker
#   - MakerPi GroundControl FastAPI backend
#   - Zigbee2MQTT (requires a Zigbee USB dongle)

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
    python3-venv \
    mosquitto \
    mosquitto-clients \
    sqlite3 \
    nodejs \
    npm \
    git \
    curl

PROJECT_DIR="$HOME/MakerPi_GroundControl"

SERVICE_USER=${SUDO_USER:-$USER}

# Configure Mosquitto (v2+ requires main config)
cat > /etc/mosquitto/mosquitto.conf << MOSQEOF
listener 1883
allow_anonymous true
persistence true
persistence_location /var/lib/mosquitto/
log_dest file /var/log/mosquitto/mosquitto.log
MOSQEOF

# Ensure Mosquitto can write to its directories
mkdir -p /var/lib/mosquitto /var/log/mosquitto
chown mosquitto:mosquitto /var/lib/mosquitto /var/log/mosquitto

# Create Python virtual environment
echo -e "${YELLOW}Setting up Python environment...${NC}"
python3 -m venv $PROJECT_DIR/venv
source $PROJECT_DIR/venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}Installing Python packages...${NC}"

# Try uv first, fall back to pip
if command -v uv &> /dev/null; then
    echo "Using uv for fast installation..."
    uv sync
else
    echo "uv not found, using pip..."
    pip install --upgrade pip
    pip install -r requirements.txt
    echo ""
    echo "💡 Tip: Install uv for faster installs:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# Create systemd service for FastAPI app
echo -e "${YELLOW}Creating systemd service...${NC}"
cat > /etc/systemd/system/groundcontrol.service << EOF
[Unit]
Description=MakerPi GroundControl Web Service
After=network.target mosquitto.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# ── Zigbee2MQTT ────────────────────────────────────────────────────────────────
echo -e "${YELLOW}Installing Zigbee2MQTT...${NC}"

Z2M_DIR="/opt/zigbee2mqtt"

# Clone or update the repo
if [ -d "$Z2M_DIR" ]; then
    echo "Zigbee2MQTT already cloned, pulling latest..."
    git -C "$Z2M_DIR" pull
else
    git clone --depth 1 https://github.com/Koenkk/zigbee2mqtt.git "$Z2M_DIR"
fi

# Install Node.js dependencies
cd "$Z2M_DIR"
npm ci --omit=dev
cd "$PROJECT_DIR"

# Create data directory
mkdir -p "$Z2M_DIR/data"

# Copy config if not already present (don't overwrite customised config)
if [ ! -f "$Z2M_DIR/data/configuration.yaml" ]; then
    cp "$PROJECT_DIR/config/zigbee2mqtt.yaml" "$Z2M_DIR/data/configuration.yaml"
    echo "Zigbee2MQTT config copied to $Z2M_DIR/data/configuration.yaml"
else
    echo "Existing Zigbee2MQTT config found, skipping copy."
fi

# Fix ownership
chown -R "$SERVICE_USER":"$SERVICE_USER" "$Z2M_DIR"

# Add user to dialout group so it can access the USB serial port
usermod -aG dialout "$SERVICE_USER"
echo "Added $SERVICE_USER to dialout group (serial port access)"

# Create systemd service for Zigbee2MQTT
echo -e "${YELLOW}Creating Zigbee2MQTT systemd service...${NC}"
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

# ── Enable and start all services ─────────────────────────────────────────────
echo -e "${YELLOW}Enabling and starting services...${NC}"
systemctl daemon-reload
systemctl enable mosquitto
systemctl restart mosquitto
systemctl enable groundcontrol
systemctl start groundcontrol
systemctl enable zigbee2mqtt
systemctl start zigbee2mqtt

# Wait a moment for services to start
sleep 5

# Check status
echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Service Status:"
echo "---------------"
systemctl status mosquitto --no-pager -l | grep -E "(Active:|loaded)"
echo ""
systemctl status groundcontrol --no-pager -l | grep -E "(Active:|loaded)"
echo ""
systemctl status zigbee2mqtt --no-pager -l | grep -E "(Active:|loaded)"
echo ""
echo -e "${GREEN}Access your dashboard at:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo -e "${GREEN}Zigbee2MQTT frontend at:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):8090"
echo ""
echo "MQTT Broker:"
echo "  Host: $(hostname -I | awk '{print $1}')"
echo "  Port: 1883"
echo ""
echo -e "${YELLOW}⚠️  Zigbee USB dongle:${NC}"
echo "  Check the correct serial port with:  ls /dev/tty{USB,ACM}*"
echo "  Then update:  $Z2M_DIR/data/configuration.yaml  (serial.port)"
echo "  And restart:  sudo systemctl restart zigbee2mqtt"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u groundcontrol -f"
echo "  sudo journalctl -u mosquitto -f"
echo "  sudo journalctl -u zigbee2mqtt -f"

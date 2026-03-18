#!/bin/bash
# MakerPi GroundControl - Setup Script for Raspberry Pi
# Run this on your Pi: sudo bash setup.sh

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
    sqlite3

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
    uv pip install -r requirements.txt
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

# Enable and start services
echo -e "${YELLOW}Enabling and starting services...${NC}"
systemctl enable mosquitto
systemctl restart mosquitto
systemctl enable groundcontrol
systemctl start groundcontrol

# Wait a moment for services to start
sleep 3

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
echo -e "${GREEN}Access your dashboard at:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "MQTT Broker:"
echo "  Host: $(hostname -I | awk '{print $1}')"
echo "  Port: 1883"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u groundcontrol -f"
echo "  sudo journalctl -u mosquitto -f"

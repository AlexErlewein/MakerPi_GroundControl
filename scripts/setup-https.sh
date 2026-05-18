#!/bin/bash
# ============================================================================
# HTTPS Setup for MakerPi GroundControl
# Installs Nginx + mkcert and configures TLS with a locally-signed certificate.
#
# Run ONCE on the Pi as root:
#   sudo bash scripts/setup-https.sh
#
# After running, distribute ~/mkcert-rootCA.crt to all client devices:
#   scp <user>@<pi-ip>:~/mkcert-rootCA.crt .
#   - macOS: double-click → Keychain Access → set "Always Trust"
#   - iOS:   open via AirDrop/Safari → install profile → Settings → Trust
#   - Android: Settings → Security → Install CA certificate
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/config.json"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root:  sudo bash scripts/setup-https.sh${NC}"
    exit 1
fi

# ── Resolve IPs from config or fallback ──────────────────────────────────────
if [ -f "$CONFIG_FILE" ] && command -v jq &>/dev/null; then
    TAILSCALE_IP=$(jq -r '.tailscale_ip // "100.78.55.14"' "$CONFIG_FILE")
    PI_HOST=$(jq -r '.pi_host // "192.168.178.47"' "$CONFIG_FILE")
    SERVICE_USER=$(jq -r '.pi_user // "dev"' "$CONFIG_FILE")
else
    TAILSCALE_IP="100.78.55.14"
    PI_HOST="192.168.178.47"
    SERVICE_USER="${SUDO_USER:-dev}"
fi

CERT_DIR="/etc/ssl/groundcontrol"
NGINX_CONF="/etc/nginx/sites-available/groundcontrol"
NGINX_ENABLED="/etc/nginx/sites-enabled/groundcontrol"

echo "============================================================"
echo " MakerPi GroundControl – HTTPS Setup"
echo "============================================================"
echo " Tailscale IP : $TAILSCALE_IP"
echo " LAN IP       : $PI_HOST"
echo " Cert dir     : $CERT_DIR"
echo "============================================================"
echo ""

# ── 1. Install nginx ──────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/6] Installing nginx...${NC}"
apt-get update -qq
apt-get install -y nginx

# ── 2. Install mkcert ────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/6] Installing mkcert...${NC}"

# Try apt first (Debian 12+ / Ubuntu 23+), fall back to binary download
if apt-get install -y mkcert 2>/dev/null; then
    echo "  mkcert installed via apt"
else
    echo "  apt package not found – downloading binary..."
    ARCH=$(dpkg --print-architecture)
    case "$ARCH" in
        amd64)  MKCERT_ARCH="amd64" ;;
        arm64)  MKCERT_ARCH="arm64" ;;
        armhf)  MKCERT_ARCH="arm" ;;
        *)      echo -e "${RED}Unsupported arch: $ARCH${NC}"; exit 1 ;;
    esac
    MKCERT_VERSION="v1.4.4"
    MKCERT_URL="https://github.com/FiloSottile/mkcert/releases/download/${MKCERT_VERSION}/mkcert-${MKCERT_VERSION}-linux-${MKCERT_ARCH}"
    curl -fsSL -o /usr/local/bin/mkcert "$MKCERT_URL"
    chmod +x /usr/local/bin/mkcert
    echo "  mkcert $MKCERT_VERSION installed to /usr/local/bin/mkcert"
fi

# ── 3. Create local CA and certificate ───────────────────────────────────────
echo -e "${YELLOW}[3/6] Creating local CA and certificate...${NC}"

# Run mkcert as the service user so the CA ends up in their home directory
# CAROOT is set so we know exactly where the CA lives
CAROOT_DIR="/home/$SERVICE_USER/.local/share/mkcert"
mkdir -p "$CAROOT_DIR"
chown "$SERVICE_USER:$SERVICE_USER" "$CAROOT_DIR"

# Install the CA (only needed once; idempotent)
CAROOT="$CAROOT_DIR" sudo -u "$SERVICE_USER" mkcert -install

# Generate certificate for both IPs + localhost
CERT_TMPDIR="$(mktemp -d)"
cd "$CERT_TMPDIR"
CAROOT="$CAROOT_DIR" sudo -u "$SERVICE_USER" mkcert \
    "$TAILSCALE_IP" \
    "$PI_HOST" \
    "localhost" \
    "127.0.0.1"

# Locate generated files (mkcert names them after the first SAN)
CERT_FILE="$(ls "$CERT_TMPDIR"/*.pem | grep -v key | head -1)"
KEY_FILE="$(ls "$CERT_TMPDIR"/*-key.pem | head -1)"

# ── 4. Install certificate ───────────────────────────────────────────────────
echo -e "${YELLOW}[4/6] Installing certificate to $CERT_DIR...${NC}"
mkdir -p "$CERT_DIR"
cp "$CERT_FILE" "$CERT_DIR/cert.pem"
cp "$KEY_FILE"  "$CERT_DIR/key.pem"
chmod 640 "$CERT_DIR/key.pem"
chmod 644 "$CERT_DIR/cert.pem"
chown root:www-data "$CERT_DIR/key.pem" "$CERT_DIR/cert.pem"
rm -rf "$CERT_TMPDIR"
echo "  Certificate installed."

# ── 5. Configure nginx ───────────────────────────────────────────────────────
echo -e "${YELLOW}[5/6] Configuring nginx...${NC}"
cp "$PROJECT_DIR/config/nginx.conf" "$NGINX_CONF"

# Disable default site if present
rm -f /etc/nginx/sites-enabled/default

# Enable groundcontrol site
ln -sf "$NGINX_CONF" "$NGINX_ENABLED"

nginx -t
echo "  Nginx config OK."

# ── 6. Enable and start nginx ────────────────────────────────────────────────
echo -e "${YELLOW}[6/6] Enabling nginx service...${NC}"
systemctl enable nginx
systemctl restart nginx
echo "  Nginx started."

# ── Export root CA for clients ───────────────────────────────────────────────
ROOT_CA_SRC="$CAROOT_DIR/rootCA.pem"
ROOT_CA_DEST="/home/$SERVICE_USER/mkcert-rootCA.crt"
if [ -f "$ROOT_CA_SRC" ]; then
    cp "$ROOT_CA_SRC" "$ROOT_CA_DEST"
    chown "$SERVICE_USER:$SERVICE_USER" "$ROOT_CA_DEST"
    echo ""
    echo -e "${GREEN}Root CA exported to: $ROOT_CA_DEST${NC}"
fi

echo ""
echo "============================================================"
echo -e "${GREEN} HTTPS setup complete!${NC}"
echo "============================================================"
echo ""
echo " Access your dashboard at:"
echo "   https://$TAILSCALE_IP    (Tailscale)"
echo "   https://$PI_HOST         (LAN)"
echo ""
echo " HTTP (port 80) redirects automatically to HTTPS."
echo ""
echo " To distribute the CA to client devices:"
echo "   scp $SERVICE_USER@$TAILSCALE_IP:~/mkcert-rootCA.crt ."
echo ""
echo " Client trust instructions:"
echo "   macOS  : double-click mkcert-rootCA.crt → Keychain → 'Always Trust'"
echo "   iOS    : AirDrop or open in Safari → install profile → Settings → Trust"
echo "   Android: Settings → Security → Install CA certificate"
echo "   Windows: double-click → Install → 'Trusted Root Certification Authorities'"
echo ""
echo " Nginx logs:  sudo journalctl -u nginx -f"
echo " App logs:    sudo journalctl -u groundcontrol -f"

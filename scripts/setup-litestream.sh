#!/usr/bin/env bash
# Install Litestream and configure it to replicate all SQLite databases to Backblaze B2.
# Run once on the Raspberry Pi as root:
#   sudo bash scripts/setup-litestream.sh
#
# Prerequisites:
#   1. Fill in config/litestream.yml (copy from config/litestream.yml.example)
#   2. Set litestream_enabled: true in config/config.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LITESTREAM_CONFIG="$PROJECT_DIR/config/litestream.yml"

# ── Detect architecture ───────────────────────────────────────────────────────
ARCH=$(uname -m)
case "$ARCH" in
    aarch64|arm64) LITESTREAM_ARCH="arm64" ;;
    armv7l|armhf)  LITESTREAM_ARCH="armv7" ;;
    x86_64)        LITESTREAM_ARCH="amd64" ;;
    *)
        echo "ERROR: Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

LITESTREAM_VERSION="0.3.13"
LITESTREAM_URL="https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-v${LITESTREAM_VERSION}-linux-${LITESTREAM_ARCH}.tar.gz"

# ── Check config ──────────────────────────────────────────────────────────────
if [ ! -f "$LITESTREAM_CONFIG" ]; then
    echo "ERROR: $LITESTREAM_CONFIG not found."
    echo "Copy config/litestream.yml.example to config/litestream.yml and fill in your credentials."
    exit 1
fi

# ── Download and install Litestream ──────────────────────────────────────────
echo "==> Downloading Litestream v${LITESTREAM_VERSION} for ${LITESTREAM_ARCH}..."
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

curl -fsSL "$LITESTREAM_URL" -o "$TMP_DIR/litestream.tar.gz"
tar -xzf "$TMP_DIR/litestream.tar.gz" -C "$TMP_DIR"
install -m 755 "$TMP_DIR/litestream" /usr/local/bin/litestream

echo "==> Installed: $(litestream version)"

# ── Install config ────────────────────────────────────────────────────────────
echo "==> Installing config to /etc/litestream.yml..."
cp "$LITESTREAM_CONFIG" /etc/litestream.yml

# ── Create systemd service ────────────────────────────────────────────────────
echo "==> Creating systemd service..."
cat > /etc/systemd/system/litestream.service << 'EOF'
[Unit]
Description=Litestream SQLite replication
After=network.target
Wants=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=5s
ExecStart=/usr/local/bin/litestream replicate -config /etc/litestream.yml

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable litestream
systemctl start litestream

echo ""
echo "==> Litestream is running. Verify with:"
echo "    sudo systemctl status litestream"
echo "    sudo journalctl -u litestream -f"
echo "    litestream snapshots -config /etc/litestream.yml"

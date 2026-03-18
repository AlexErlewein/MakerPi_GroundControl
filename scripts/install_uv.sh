#!/bin/bash
# Install uv (fast Python package installer) on Raspberry Pi
# Run this on your Pi: bash install_uv.sh

set -e

echo "📦 Installing uv (fast Python package installer)..."

# Try the official installer first (works on ARMv7+)
if curl -LsSf https://astral.sh/uv/install.sh | sh; then
    echo "✅ uv installed successfully via official installer"
else
    echo "⚠️  Official installer failed, trying pip install..."
    pip3 install --break-system-packages uv
fi

# Add to PATH for current session
export PATH="$HOME/.local/bin:$PATH"

# Add to .bashrc for persistent PATH
if ! grep -q '.local/bin' ~/.bashrc 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    echo "Added uv to PATH in .bashrc"
fi

# Verify installation
echo ""
echo "Checking installation:"
uv --version || echo "⚠️  uv command not found in PATH"

echo ""
echo "✅ Setup complete!"
echo "Run 'source ~/.bashrc' or restart your shell to use uv."

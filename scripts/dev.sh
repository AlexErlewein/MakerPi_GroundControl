#!/bin/bash
# Local development server – runs the app with hot-reload on localhost.
# Usage:
#   ./scripts/dev.sh              – start on port 8000
#   ./scripts/dev.sh --port 3000  – start on custom port

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PORT=8000
for i in "$@"; do
    if [ "$prev" = "--port" ]; then PORT="$i"; fi
    prev="$i"
done

# Activate venv if present
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
elif [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Check uvicorn is available
if ! command -v uvicorn &> /dev/null; then
    echo "❌ uvicorn not found. Install dependencies first:"
    echo "   pip install -e ."
    exit 1
fi

echo "🚀 Starting GroundControl dev server..."
echo "   http://localhost:$PORT"
echo "   Press Ctrl+C to stop"
echo ""

cd "$PROJECT_ROOT"
uvicorn backend.main:app --host 127.0.0.1 --port "$PORT" --reload

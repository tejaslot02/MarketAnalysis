#!/usr/bin/env bash
set -e

echo "=============================================================================="
echo "  NSE India Option Chain & Quantitative Analytics Terminal"
echo "=============================================================================="

# Activate virtualenv if present
if [ -d ".venv" ]; then
    echo "[*] Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "[*] Activating virtual environment (venv)..."
    source venv/bin/activate
fi

PORT="${1:-8080}"

echo "[*] Starting Web UI Server on http://127.0.0.1:${PORT}/"

# Auto-open browser if available
if command -v xdg-open > /dev/null 2>&1; then
    (sleep 1.5 && xdg-open "http://127.0.0.1:${PORT}/") &
elif command -v open > /dev/null 2>&1; then
    (sleep 1.5 && open "http://127.0.0.1:${PORT}/") &
fi

python3 server.py --port "${PORT}"

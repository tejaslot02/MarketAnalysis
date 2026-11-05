#!/usr/bin/env bash
set -e

echo "=============================================================================="
echo "  NSE India Option Chain & Options Strategy Intelligence Terminal"
echo "=============================================================================="

# Activate virtualenv if present
if [ -d ".venv" ]; then
    echo "[*] Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "[*] Activating virtual environment (venv)..."
    source venv/bin/activate
fi

# Argument parsing and dispatch
if [ $# -eq 0 ]; then
    PORT=8080
    echo "[*] Starting Web UI Server on http://127.0.0.1:${PORT}/ [Default Sample Mode]"
    echo "[*] Browser will launch automatically..."
    python3 server.py --port "${PORT}" --open
elif [[ "$1" =~ ^[0-9]+$ ]]; then
    PORT="$1"
    shift
    echo "[*] Starting Web UI Server on http://127.0.0.1:${PORT}/"
    echo "[*] Browser will launch automatically..."
    python3 server.py --port "${PORT}" --open "$@"
else
    echo "[*] Starting Web UI Server with custom arguments: $*"
    python3 server.py "$@"
fi

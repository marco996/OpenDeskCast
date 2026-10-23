#!/usr/bin/env bash
# OpenDeskCast — Script di avvio rapido per macOS (da sorgente)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "Errore: Python 3 non trovato. Installalo con 'brew install python' o da python.org"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "=== Creazione ambiente virtuale per macOS ==="
    "$PYTHON_CMD" -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

exec python run.py "$@"

#!/usr/bin/env bash
# OpenDeskCast - Avvio rapido per distribuzioni Linux (Ubuntu, Debian, Fedora, Arch)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Avvio di OpenDeskCast per Linux ==="

# 1. Verifica Python 3
if ! command -v python3 &>/dev/null; then
    echo "ERRORE: Python 3 non trovato. Installa con: sudo apt install python3 python3-pip python3-venv (Ubuntu/Debian) o sudo dnf install python3 (Fedora)"
    exit 1
fi

# 2. Crea/Attiva virtual environment
if [ ! -d ".venv" ]; then
    echo "[setup] Creazione ambiente virtuale isolato .venv..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# 3. Installa dipendenze se necessario
if ! python3 -c "import fastapi, uvicorn, mss" &>/dev/null; then
    echo "[setup] Installazione dipendenze richieste (FastAPI, MSS, OpenCV, WebSockets)..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# 4. Avvia server e pannello host
echo "[start] Avvio OpenDeskCast..."
exec python3 run.py "$@"

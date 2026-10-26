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

# 2. Crea/Attiva virtual environment (con --system-site-packages per accedere a PyGObject/PipeWire su Fedora/Ubuntu Wayland)
if [ ! -d ".venv" ]; then
    echo "[setup] Creazione ambiente virtuale .venv..."
    python3 -m venv --system-site-packages .venv
elif [ -f ".venv/pyvenv.cfg" ]; then
    sed -i 's/include-system-site-packages = false/include-system-site-packages = true/g' .venv/pyvenv.cfg 2>/dev/null || true
fi

source .venv/bin/activate

# 3. Installa dipendenze Python se necessario
if ! python3 -c "import fastapi, uvicorn, mss, cv2" &>/dev/null; then
    echo "[setup] Installazione dipendenze richieste (FastAPI, MSS, OpenCV, WebSockets)..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# 4. Verifica supporto Wayland / PipeWire (Fedora, Ubuntu Wayland, KDE, GNOME)
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
    echo "[wayland] Sessione Wayland rilevata: utilizzo XDG Desktop Portal + PipeWire."
    if ! /usr/bin/python3 -c "import gi; from gi.repository import Gio, GLib" &>/dev/null; then
        echo "AVVISO: PyGObject (gi) non trovato per la cattura nativa Wayland."
        echo "  -> Su Fedora: sudo dnf install python3-gobject gstreamer1-plugins-base gstreamer1-plugins-good pipewire-gstreamer"
        echo "  -> Su Ubuntu/Debian: sudo apt install python3-gi gir1.2-gst-plugins-base-1.0 gstreamer1.0-pipewire"
    fi
fi

# 5. Avvia server e pannello host
echo "[start] Avvio OpenDeskCast..."
exec python3 run.py "$@"

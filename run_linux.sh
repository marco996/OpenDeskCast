#!/usr/bin/env bash
# OpenDeskCast - Avvio rapido per distribuzioni Linux (Ubuntu, Debian, Fedora, Arch)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Avvio di OpenDeskCast per Linux ==="

# 1. Seleziona il Python di sistema (/usr/bin/python3) se contiene PyGObject (gi),
#    evitando conflitti con ambienti Conda/Miniforge che non hanno i binding GStreamer/Wayland.
PYTHON_BIN=""
if [ -x "/usr/bin/python3" ] && /usr/bin/python3 -c "import gi" &>/dev/null; then
    PYTHON_BIN="/usr/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "ERRORE: Python 3 non trovato. Installa con: sudo apt install python3 python3-pip python3-venv (Ubuntu/Debian) o sudo dnf install python3 (Fedora)"
    exit 1
fi

# 2. Crea o aggiorna il virtual environment .venv con --system-site-packages
#    Se .venv esisteva già (es. creato da Miniforge senza 'gi'), lo ricrea con il Python di sistema.
if [ -d ".venv" ] && [ "$PYTHON_BIN" = "/usr/bin/python3" ]; then
    if ! .venv/bin/python3 -c "import gi" &>/dev/null; then
        echo "[setup] Ricreazione .venv con il Python di sistema (/usr/bin/python3) per abilitare il supporto Wayland/PipeWire..."
        rm -rf .venv
    fi
fi

if [ ! -d ".venv" ]; then
    echo "[setup] Creazione ambiente virtuale .venv (usando $PYTHON_BIN --system-site-packages)..."
    "$PYTHON_BIN" -m venv --system-site-packages .venv
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
    if ! python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gio, GLib, Gst" &>/dev/null; then
        echo "AVVISO: PyGObject (gi) o GStreamer non trovato per la cattura nativa Wayland."
        echo "  -> Su Fedora: sudo dnf install python3-gobject gstreamer1-plugins-base gstreamer1-plugins-good pipewire-gstreamer"
        echo "  -> Su Ubuntu/Debian: sudo apt install python3-gi gir1.2-gst-plugins-base-1.0 gstreamer1.0-pipewire"
    fi
fi

# 5. Avvia server e pannello host
echo "[start] Avvio OpenDeskCast..."
exec python3 run.py "$@"

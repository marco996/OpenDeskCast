from __future__ import annotations

import io
import os
from pathlib import Path
import stat
import time
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build" / "macos_app"


def read_version() -> str:
    vfile = ROOT / "VERSION"
    return vfile.read_text(encoding="utf-8").strip() if vfile.is_file() else "1.0.0"


def create_macos_app_zip() -> Path:
    version = read_version()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    out_zip = DIST_DIR / f"OpenDeskCast-v{version}-macos.zip"

    print(f"=== [macOS] Creazione pacchetto nativo OpenDeskCast.app (v{version}) ===")

    launcher_sh = """#!/usr/bin/env bash
# OpenDeskCast — macOS Native Bundle Launcher
set -e

APP_DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
cd "$APP_DIR"

# 1. Trova Python 3 su macOS (Homebrew, Framework o Command Line Tools)
PYTHON_BIN=""
for candidate in \
    "/opt/homebrew/bin/python3" \
    "/usr/local/bin/python3" \
    "/usr/bin/python3" \
    "$(command -v python3 2>/dev/null)" \
    "$(command -v python 2>/dev/null)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    osascript -e 'display alert "OpenDeskCast" message "Python 3 non trovato. Installa Python da https://www.python.org o con brew install python." as critical'
    exit 1
fi

# 2. Configura ambiente virtuale isolato per OpenDeskCast in Library/Application Support
VENV_DIR="$HOME/Library/Application Support/OpenDeskCast/venv"
if [ ! -f "$VENV_DIR/bin/python" ]; then
    mkdir -p "$HOME/Library/Application Support/OpenDeskCast"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip --quiet
    "$VENV_DIR/bin/pip" install -r requirements.txt --quiet
fi

# 3. Avvia OpenDeskCast
exec "$VENV_DIR/bin/python" run.py "$@"
""".encode("utf-8")

    info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>OpenDeskCast</string>
    <key>CFBundleDisplayName</key>
    <string>OpenDeskCast</string>
    <key>CFBundleIdentifier</key>
    <string>com.opendeskcast.app</string>
    <key>CFBundleVersion</key>
    <string>{version}</string>
    <key>CFBundleShortVersionString</key>
    <string>{version}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>OpenDeskCast</string>
    <key>CFBundleIconFile</key>
    <string>opendeskcast.icns</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSScreenCaptureUsageDescription</key>
    <string>OpenDeskCast richiede l'accesso alla registrazione dello schermo per trasmettere il display ai tuoi dispositivi.</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>OpenDeskCast richiede l'accesso all'audio per trasmettere l'audio del computer.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>OpenDeskCast utilizza AppleScript per controllare l'audio di sistema.</string>
</dict>
</plist>
""".encode("utf-8")

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        now = time.localtime(time.time())[:6]

        def add_dir(arc_path: str):
            zi = zipfile.ZipInfo(f"{arc_path}/", now)
            zi.external_attr = (stat.S_IFDIR | 0o755) << 16
            zf.writestr(zi, b"")

        def add_file(arc_path: str, data: bytes, is_exec: bool = False):
            zi = zipfile.ZipInfo(arc_path, now)
            mode = 0o755 if is_exec else 0o644
            zi.external_attr = (stat.S_IFREG | mode) << 16
            zf.writestr(zi, data)

        # Base directories
        add_dir("OpenDeskCast.app")
        add_dir("OpenDeskCast.app/Contents")
        add_dir("OpenDeskCast.app/Contents/MacOS")
        add_dir("OpenDeskCast.app/Contents/Resources")
        add_dir("OpenDeskCast.app/Contents/Resources/app")
        add_dir("OpenDeskCast.app/Contents/Resources/static")

        # Info.plist
        add_file("OpenDeskCast.app/Contents/Info.plist", info_plist)

        # Executable launcher
        add_file("OpenDeskCast.app/Contents/MacOS/OpenDeskCast", launcher_sh, is_exec=True)

        # Icon
        icns_file = ROOT / "opendeskcast.icns"
        if icns_file.is_file():
            add_file("OpenDeskCast.app/Contents/Resources/opendeskcast.icns", icns_file.read_bytes())
            add_file("OpenDeskCast.app/Contents/Resources/icon.icns", icns_file.read_bytes())

        # App modules
        app_dir = ROOT / "app"
        for pyf in app_dir.glob("*.py"):
            add_file(f"OpenDeskCast.app/Contents/Resources/app/{pyf.name}", pyf.read_bytes())

        # Static assets
        static_dir = ROOT / "static"
        for sf in static_dir.iterdir():
            if sf.is_file():
                add_file(f"OpenDeskCast.app/Contents/Resources/static/{sf.name}", sf.read_bytes())

        # Root files
        for rf in ("run.py", "VERSION", "LICENSE", "README.md", "requirements.txt", "run_macos.sh"):
            rf_path = ROOT / rf
            if rf_path.is_file():
                is_ex = rf.endswith(".sh")
                add_file(f"OpenDeskCast.app/Contents/Resources/{rf}", rf_path.read_bytes(), is_exec=is_ex)

    print(f"[macOS] Pacchetto creato con successo: {out_zip} ({out_zip.stat().st_size // 1024} KB)")
    return out_zip


if __name__ == "__main__":
    create_macos_app_zip()

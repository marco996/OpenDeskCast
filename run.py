from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import webbrowser

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import uvicorn

from app import server as srv
from app.capture import enable_dpi_awareness, list_monitors


def _open_pc_control_window(port: int) -> None:
    """Open the PC Control Panel in a standalone app window across Windows, Linux, and macOS."""
    admin_url = f"http://127.0.0.1:{port}/admin"
    candidates = [
        shutil.which("msedge"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("microsoft-edge"),
        shutil.which("brave-browser"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]
    for exe in candidates:
        if exe and Path(exe).is_file():
            try:
                subprocess.Popen(
                    [
                        str(exe),
                        f"--app={admin_url}",
                        "--window-size=636,398",
                        "--disable-extensions",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except Exception:
                pass
    webbrowser.open(admin_url)


def main() -> None:
    enable_dpi_awareness()

    parser = argparse.ArgumentParser(description="OpenDeskCast — PC Host & Passive HDMI-Style Viewer")
    parser.add_argument("--host", default="0.0.0.0", help="Indirizzo di bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=srv.DEFAULT_PORT, help="Porta HTTP/WS")
    parser.add_argument("--no-window", action="store_true", help="Non aprire automaticamente la finestra di regia")
    args = parser.parse_args()

    ips = srv.get_local_ipv4_addresses()
    monitors = list_monitors()

    print("=" * 68)
    print("  OpenDeskCast — Regia PC & Trasmissione Sicura verso Spettatori")
    print("=" * 68)
    print(f"  Monitor Rilevati ({len(monitors)}):")
    for m in monitors:
        print(f"    - [{m['id']}] {m['name']} @ ({m['left']},{m['top']})")
    print("-" * 68)
    print(f"  Finestra di Controllo PC (Solo Localhost): http://127.0.0.1:{args.port}/admin")
    print(f"  Indirizzo Base Senza Fotocamera: http://{ips[0]}:{args.port} (PIN: {srv.host_state.session_pin})")
    print("  Indirizzi Protetti QR per Spettatori:")
    for ip in ips:
        print(f"    http://{ip}:{args.port}/?t={srv.host_state.session_token}")
    print("=" * 68)

    config = uvicorn.Config(
        srv.app,
        host=args.host,
        port=args.port,
        log_level="warning",
        log_config=None,
        ws_ping_interval=20,
        ws_ping_timeout=20,
        ws_per_message_deflate=False,
    )
    uvi_server = uvicorn.Server(config)

    def _request_stop() -> None:
        uvi_server.should_exit = True

    srv.shutdown_callback = _request_stop

    if not args.no_window:
        def _launch_window() -> None:
            time.sleep(0.8)
            _open_pc_control_window(args.port)

        threading.Thread(target=_launch_window, daemon=True).start()

    try:
        uvi_server.run()
    finally:
        try:
            asyncio.run(srv.cleanup_all())
        except Exception:
            pass


if __name__ == "__main__":
    main()

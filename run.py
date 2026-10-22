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


def _clean_subprocess_env() -> dict[str, str]:
    """Return an environment stripped of PyInstaller LD_LIBRARY_PATH to prevent child browser crashes on Linux."""
    env = os.environ.copy()
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env.pop("LD_LIBRARY_PATH_ORIG")
    else:
        env.pop("LD_LIBRARY_PATH", None)
    return env


def _is_opendeskcast_already_running(port: int) -> bool:
    """Check if an instance of OpenDeskCast is already active on localhost:port."""
    import urllib.request
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/status?port={port}", method="GET")
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False


def _open_pc_control_window(port: int) -> None:
    """Open the PC Control Panel in a standalone app window across Windows, Linux, and macOS."""
    admin_url = f"http://127.0.0.1:{port}/admin"
    clean_env = _clean_subprocess_env()

    # 1. Try Chrome/Chromium/Edge/Brave in standalone --app window mode
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
                    env=clean_env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except Exception:
                pass

    # 2. On Linux, try xdg-open with clean environment (opens system default browser)
    if shutil.which("xdg-open"):
        try:
            subprocess.Popen(
                ["xdg-open", admin_url],
                env=clean_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except Exception:
            pass

    # 3. Fallback to standard Python webbrowser with clean env
    old_ld = os.environ.get("LD_LIBRARY_PATH")
    try:
        if "LD_LIBRARY_PATH" in os.environ:
            del os.environ["LD_LIBRARY_PATH"]
        webbrowser.open(admin_url)
    finally:
        if old_ld is not None:
            os.environ["LD_LIBRARY_PATH"] = old_ld


def main() -> None:
    enable_dpi_awareness()

    parser = argparse.ArgumentParser(description="OpenDeskCast — PC Host & Passive HDMI-Style Viewer")
    parser.add_argument("--host", default="0.0.0.0", help="Indirizzo di bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=srv.DEFAULT_PORT, help="Porta HTTP/WS")
    parser.add_argument("--no-window", action="store_true", help="Non aprire automaticamente la finestra di regia")
    args = parser.parse_args()

    if _is_opendeskcast_already_running(args.port):
        print("=" * 68)
        print("  OpenDeskCast — Già in esecuzione")
        print("=" * 68)
        print(f"  Finestra di Controllo PC: http://127.0.0.1:{args.port}/admin")
        print("=" * 68)
        if not args.no_window:
            _open_pc_control_window(args.port)
        return

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
            for _ in range(25):
                time.sleep(0.2)
                if _is_opendeskcast_already_running(args.port):
                    break
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

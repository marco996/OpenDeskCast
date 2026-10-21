from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DIST_PKG = ROOT / "dist" / "OpenDeskCast"
TEST_PORT = 18765


def build_clean_env() -> dict[str, str]:
    """Return an OS environment stripped of any user Python installation."""
    clean: dict[str, str] = {}
    if sys.platform == "win32":
        sys_root = os.environ.get("SystemRoot", r"C:\Windows")
        clean["SystemRoot"] = sys_root
        clean["WINDIR"] = sys_root
        clean["PATH"] = f"{sys_root}\\System32;{sys_root}"
        clean["TEMP"] = os.environ.get("TEMP", r"C:\Windows\Temp")
        clean["TMP"] = clean["TEMP"]
        clean["USERPROFILE"] = os.environ.get("USERPROFILE", r"C:\Users\Default")
    else:
        clean["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
        clean["HOME"] = os.environ.get("HOME", "/tmp")
        clean["TMPDIR"] = "/tmp"
        if "DISPLAY" in os.environ:
            clean["DISPLAY"] = os.environ["DISPLAY"]
    return clean


def verify_clean_package() -> None:
    if not DIST_PKG.is_dir():
        raise RuntimeError(f"Pacchetto non trovato in {DIST_PKG}. Eseguire prima scripts/build_package.py.")

    with tempfile.TemporaryDirectory(prefix="opendeskcast_clean_") as tmp_dir:
        isolated_dir = Path(tmp_dir) / "OpenDeskCast"
        shutil.copytree(DIST_PKG, isolated_dir)

        if sys.platform == "win32":
            engine_bin = isolated_dir / "engine" / "OpenDeskCastEngine.exe"
            launcher_bin = isolated_dir / "OpenDeskCast.exe"
            assert launcher_bin.is_file(), "OpenDeskCast.exe mancante nel pacchetto."
        else:
            engine_bin = isolated_dir / "OpenDeskCast"

        assert engine_bin.is_file(), f"Eseguibile standalone mancante: {engine_bin}"

        clean_env = build_clean_env()

        proc = subprocess.Popen(
            [str(engine_bin), "--port", str(TEST_PORT), "--no-window"],
            cwd=str(engine_bin.parent),
            env=clean_env,
        )

        try:
            base = f"http://127.0.0.1:{TEST_PORT}"
            status_data = None
            deadline = time.monotonic() + 15.0
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError(
                        f"Il motore standalone si è arrestato prematuramente (code {proc.returncode})."
                    )
                try:
                    with urllib.request.urlopen(f"{base}/api/status?port={TEST_PORT}", timeout=1.5) as resp:
                        if resp.status == 200:
                            status_data = json.loads(resp.read().decode("utf-8"))
                            break
                except Exception:
                    time.sleep(0.3)

            assert status_data is not None, "Timeout in attesa di /api/status dal pacchetto standalone."
            assert "session_pin" in status_data and len(status_data["session_pin"]) == 4
            assert len(status_data.get("monitors", [])) >= 1

            # Verify PIN authentication
            pin_payload = json.dumps({"pin": status_data["session_pin"]}).encode("utf-8")
            req_pin = urllib.request.Request(
                f"{base}/api/verify-pin",
                data=pin_payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req_pin, timeout=2.0) as resp:
                pin_res = json.loads(resp.read().decode("utf-8"))
                assert pin_res.get("ok") is True and pin_res.get("token")

            # Verify QR PNG generation
            primary_url = urllib.parse.quote(status_data["urls"][0], safe="")
            with urllib.request.urlopen(f"{base}/api/qr.png?url={primary_url}", timeout=2.0) as resp:
                png_bytes = resp.read()
                assert png_bytes.startswith(b"\x89PNG"), "QR PNG non valido."

            # Clean shutdown via API
            req_stop = urllib.request.Request(f"{base}/api/shutdown", data=b"", method="POST")
            with urllib.request.urlopen(req_stop, timeout=2.0) as resp:
                assert resp.status == 200

            proc.wait(timeout=5)
            print(
                f"[verify-clean] OK — Standalone package booted in isolated temp folder without Python in PATH "
                f"(version={status_data.get('app_version')}, monitors={len(status_data['monitors'])})."
            )
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    verify_clean_package()

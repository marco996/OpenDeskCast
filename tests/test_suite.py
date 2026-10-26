from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import MagicMock, patch
import zipfile

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.server import app, APP_VERSION, host_state
from app.audio import AudioDeviceManager
from app.updater import check_for_updates, parse_version_tuple, pick_os_asset


class TestVersionAndUpdater(unittest.TestCase):
    def test_version_tuples(self):
        self.assertEqual(parse_version_tuple("v1.0.0"), (1, 0, 0))
        self.assertEqual(parse_version_tuple("1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version_tuple("v2.10.4-rc1"), (2, 10, 4))
        self.assertTrue(parse_version_tuple("1.0.1") > parse_version_tuple("1.0.0"))
        self.assertTrue(parse_version_tuple("1.10.0") > parse_version_tuple("1.9.0"))
        self.assertTrue(parse_version_tuple("2.0.0") > parse_version_tuple("1.99.99"))
        self.assertFalse(parse_version_tuple("1.0.0") > parse_version_tuple("1.0.0"))
        self.assertFalse(parse_version_tuple("0.9.9") > parse_version_tuple("1.0.0"))

    def test_pick_os_asset(self):
        assets = [
            {"name": "OpenDeskCast-v1.1.0-macos.zip", "browser_download_url": "https://gh/macos.zip"},
            {"name": "OpenDeskCast-v1.1.0-windows-x64.msi", "browser_download_url": "https://gh/win.msi"},
            {"name": "opendeskcast_1.1.0_amd64.deb", "browser_download_url": "https://gh/linux.deb"},
        ]
        self.assertEqual(pick_os_asset(assets, "win32"), "https://gh/win.msi")
        self.assertEqual(pick_os_asset(assets, "darwin"), "https://gh/macos.zip")
        self.assertEqual(pick_os_asset(assets, "linux"), "https://gh/linux.deb")

    def test_updater_graceful_on_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("Network unreachable")):
            info = check_for_updates("1.0.0", force=True)
            self.assertTrue(info["checked"])
            self.assertFalse(info["update_available"])
            self.assertIsNone(info["latest_version"])

    def test_updater_detects_newer_version(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = (
            b'{"tag_name": "v1.2.0", "html_url": "https://github.com/marco996/OpenDeskCast/releases/tag/v1.2.0", '
            b'"assets": [{"name": "OpenDeskCast-v1.2.0-windows-x64.msi", "browser_download_url": "https://gh/win.msi"}]}'
        )
        mock_resp.__enter__.return_value = mock_resp
        with patch("urllib.request.urlopen", return_value=mock_resp):
            info = check_for_updates("1.0.0", force=True)
            self.assertTrue(info["checked"])
            self.assertTrue(info["update_available"])
            self.assertEqual(info["latest_version"], "1.2.0")
            self.assertEqual(info["download_url"], "https://gh/win.msi")

    def test_updater_ignores_same_or_older_version(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = (
            b'{"tag_name": "v1.0.0", "html_url": "https://github.com/marco996/OpenDeskCast/releases/tag/v1.0.0", "assets": []}'
        )
        mock_resp.__enter__.return_value = mock_resp
        with patch("urllib.request.urlopen", return_value=mock_resp):
            info = check_for_updates("1.0.0", force=True)
            self.assertTrue(info["checked"])
            self.assertFalse(info["update_available"])


class TestServerEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_status_endpoint(self):
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("app_version", data)
        self.assertIn("ips", data)
        self.assertIn("session_pin", data)
        self.assertIn("update_info", data)
        self.assertEqual(len(data["session_pin"]), 4)

    def test_check_update_endpoint(self):
        res = self.client.get("/api/check-update")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("update_available", data)
        self.assertEqual(data["current_version"], APP_VERSION)

    def test_pin_verification(self):
        valid_pin = host_state.session_pin
        res_ok = self.client.post("/api/verify-pin", json={"pin": valid_pin})
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.json().get("token"), host_state.session_token)

        res_bad = self.client.post("/api/verify-pin", json={"pin": "0000" if valid_pin != "0000" else "1111"})
        self.assertEqual(res_bad.status_code, 403)

    def test_token_rotation(self):
        old_tok = host_state.session_token
        res = self.client.post("/api/rotate-token")
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(res.json()["session_token"], old_tok)

    def test_viewer_html_served(self):
        res = self.client.get(f"/?t={host_state.session_token}")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("content-type", ""))

    def test_admin_html_served_and_contains_version_elements(self):
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("app-current-version", html)
        self.assertIn("btn-update-download", html)
        self.assertIn("version-footer", html)


class TestReleaseArtifacts(unittest.TestCase):
    def test_dist_artifacts_exist_and_non_empty(self):
        msi = ROOT / "dist" / f"OpenDeskCast-v{APP_VERSION}-windows-x64.msi"
        deb = ROOT / "dist" / f"opendeskcast_{APP_VERSION}_amd64.deb"
        mac_zip = ROOT / "dist" / f"OpenDeskCast-v{APP_VERSION}-macos.zip"

        self.assertTrue(msi.is_file(), f"Missing MSI: {msi}")
        self.assertGreater(msi.stat().st_size, 50 * 1024 * 1024)

        self.assertTrue(deb.is_file(), f"Missing DEB: {deb}")
        self.assertGreater(deb.stat().st_size, 50 * 1024 * 1024)

        self.assertTrue(mac_zip.is_file(), f"Missing macOS zip: {mac_zip}")
        self.assertGreater(mac_zip.stat().st_size, 1 * 1024 * 1024)

        with zipfile.ZipFile(mac_zip) as z:
            names = z.namelist()
            self.assertTrue(any("OpenDeskCast.app" in n for n in names))
            self.assertTrue(any("Info.plist" in n for n in names))
            for zi in z.infolist():
                self.assertEqual(zi.create_system, 3, f"Non-Unix create_system on {zi.filename}")
            for exec_entry in (
                "Installa OpenDeskCast.command",
                "OpenDeskCast.app/Contents/MacOS/OpenDeskCast",
                "OpenDeskCast.app/Contents/Resources/bootstrap_macos.sh",
                "OpenDeskCast.app/Contents/Resources/run_macos.sh",
            ):
                zi = z.getinfo(exec_entry)
                mode = (zi.external_attr >> 16) & 0o777
                self.assertEqual(mode, 0o755, f"Expected 0755 on {exec_entry}, got {oct(mode)}")
                self.assertNotIn(b"\r\n", z.read(exec_entry))
            launcher_c = z.read("OpenDeskCast.app/Contents/Resources/macos_launcher.c").decode("utf-8")
            self.assertIn("CGRequestScreenCaptureAccess", launcher_c)
            self.assertIn("Py_BytesMain", launcher_c)


class TestNativeAudioSystem(unittest.TestCase):
    def test_audio_device_manager_initializes(self):
        adm = AudioDeviceManager()
        self.assertFalse(adm.has_virtual_cable())

    def test_zero_driver_dependency(self):
        drivers_dir = ROOT / "drivers"
        self.assertFalse(drivers_dir.exists(), "drivers directory should be completely removed")


class TestMobilePinAndWayland(unittest.TestCase):
    def test_mobile_pin_js_has_no_undefined_functions_and_supports_touch(self):
        client_js = (ROOT / "static" / "client.js").read_text(encoding="utf-8")
        self.assertIn("function requestWakeLockAndFullscreen()", client_js)
        self.assertIn("touchend", client_js)
        self.assertIn("pin-native-input", client_js)

        style_css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-height: 480px)", style_css)
        self.assertIn("touch-action: manipulation", style_css)

    def test_wayland_portal_capturer_module(self):
        from app.wayland_capture import WaylandScreenCast, is_wayland, PortalError
        from app.capture import _wayland_enabled
        self.assertIsInstance(is_wayland(), bool)
        self.assertIsInstance(_wayland_enabled(), bool)
        wsc = WaylandScreenCast.get()
        self.assertIs(wsc, WaylandScreenCast.get())


if __name__ == "__main__":
    unittest.main()

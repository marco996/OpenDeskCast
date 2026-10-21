import struct
import cv2
import numpy as np
from fastapi.testclient import TestClient
from app.qr_svg import generate_qr_matrix
from app.server import app, host_state, _is_localhost


def test_localhost_boundary_guard():
    assert _is_localhost("127.0.0.1") is True
    assert _is_localhost("::1") is True
    assert _is_localhost("192.168.1.55") is False
    assert _is_localhost("10.0.0.12") is False
    assert _is_localhost(None) is False


def test_api_status_returns_unique_monitors_and_token_urls():
    client = TestClient(app)
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert "monitors" in data and len(data["monitors"]) >= 1
    mon_ids = [m["id"] for m in data["monitors"]]
    assert len(mon_ids) == len(set(mon_ids))
    assert "urls" in data and len(data["urls"]) >= 1
    assert f"?t={host_state.session_token}" in data["urls"][0]


def test_pc_can_update_stream_settings():
    client = TestClient(app)
    res = client.post(
        "/api/settings",
        json={
            "monitor_id": 0,
            "fps": 45,
            "quality": 85,
            "scale": 0.8,
            "draw_cursor": False,
            "audio_enabled": False,
            "lock_new_viewers": False,
        },
    )
    assert res.status_code == 200
    updated = res.json()["settings"]
    assert updated["monitor_id"] == 0
    assert updated["fps"] == 45
    assert updated["quality"] == 85
    assert updated["scale"] == 0.8
    assert updated["draw_cursor"] is False


def test_qr_svg_and_png_endpoints():
    target_url = "http://192.168.1.10:8765/?t=AbCdEf12345"
    client = TestClient(app)
    res = client.get(f"/api/qr.svg?url={target_url}")
    assert res.status_code == 200
    assert "<svg" in res.text

    mat = np.array(generate_qr_matrix(target_url, border=4), dtype=np.uint8)
    img = (1 - mat) * 255
    img_scaled = cv2.resize(
        img, (img.shape[1] * 10, img.shape[0] * 10), interpolation=cv2.INTER_NEAREST
    )
    detector = cv2.QRCodeDetector()
    decoded, _, _ = detector.detectAndDecode(img_scaled)
    assert decoded == target_url

    qr_png_res = client.get(f"/api/qr.png?url={target_url}")
    assert qr_png_res.status_code == 200
    assert qr_png_res.headers["content-type"] == "image/png"
    assert qr_png_res.content[:4] == b"\x89PNG"


def test_security_token_and_pin_authentication():
    client = TestClient(app)
    host_state.lock_new_viewers = False

    # Opening base URL without token serves the 4-digit PIN screen
    res_pin_page = client.get("/")
    assert res_pin_page.status_code == 200
    assert "pin-overlay" in res_pin_page.text

    # Wrong token in URL is rejected with 403
    res_bad_token = client.get("/?t=wrong_token")
    assert res_bad_token.status_code == 403

    # Wrong 4-digit PIN is rejected with 403
    res_bad_pin = client.post("/api/verify-pin", json={"pin": "0000"})
    assert res_bad_pin.status_code == 403

    # Correct 4-digit PIN returns the active session token
    valid_pin = host_state.session_pin
    assert len(valid_pin) == 4 and valid_pin.isdigit()
    res_good_pin = client.post("/api/verify-pin", json={"pin": valid_pin})
    assert res_good_pin.status_code == 200
    assert res_good_pin.json()["token"] == host_state.session_token

    valid_token = host_state.session_token
    res_ok = client.get(f"/?t={valid_token}")
    assert res_ok.status_code == 200
    assert "viewer-canvas" in res_ok.text

    # Rotating token invalidates previous token and rotates 4-digit PIN
    rot_res = client.post("/api/rotate-token")
    assert rot_res.status_code == 200
    new_token = rot_res.json()["session_token"]
    new_pin = rot_res.json()["session_pin"]
    assert new_token != valid_token
    assert len(new_pin) == 4 and new_pin.isdigit()

    res_expired = client.get(f"/?t={valid_token}")
    assert res_expired.status_code == 403

    res_new = client.get(f"/?t={new_token}")
    assert res_new.status_code == 200


def test_websocket_stream_requires_valid_token():
    client = TestClient(app)
    host_state.lock_new_viewers = False
    token = host_state.session_token

    with client.websocket_connect(f"/ws/stream?t={token}") as ws:
        data = ws.receive_bytes()
        assert len(data) > 100
        w, h, _ = struct.unpack("<HHI", data[:8])
        assert w > 0 and h > 0
        assert data[8:10] == b"\xff\xd8"

        host_state.version += 1
        data2 = ws.receive_bytes()
        assert len(data2) > 100
        assert data2[8:10] == b"\xff\xd8"

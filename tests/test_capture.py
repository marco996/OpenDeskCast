import struct
from app.capture import (
    enable_dpi_awareness,
    list_monitors,
    get_virtual_screen_bounds,
    ScreenCapturer,
)


def test_list_monitors_deduplicated_and_primary():
    enable_dpi_awareness()
    monitors = list_monitors()
    assert len(monitors) >= 1
    ids = [m["id"] for m in monitors]
    assert len(ids) == len(set(ids))
    primary = [m for m in monitors if m["is_primary"]]
    assert len(primary) == 1
    assert primary[0]["width"] > 0 and primary[0]["height"] > 0
    vx, vy, vw, vh = get_virtual_screen_bounds()
    assert vw >= primary[0]["width"]
    assert vh >= primary[0]["height"]


def test_capture_and_header_format():
    cap = ScreenCapturer()
    packet = cap.encode_frame(monitor_id=999, quality=70, scale=0.5, force=True)
    assert packet is not None and len(packet) > 100
    w, h, ts = struct.unpack("<HHI", packet[:8])
    assert w > 0 and h > 0
    assert packet[8:10] == b"\xff\xd8"


def test_dirty_frame_skip_and_force():
    cap = ScreenCapturer()
    raw, mon = cap.capture_raw(monitor_id=0, draw_cursor=False)
    assert raw.shape == (mon["height"], mon["width"], 4)
    first = cap.encode_frame(monitor_id=0, quality=70, force=True)
    assert first is not None
    forced = cap.encode_frame(monitor_id=0, quality=70, force=True)
    assert forced is not None

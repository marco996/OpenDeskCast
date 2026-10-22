import asyncio
from pathlib import Path
import pytest
from app.audio import AudioStreamer, AudioDeviceManager, CHUNK_BYTES, SAMPLE_RATE


def test_audio_streamer_device_probe():
    streamer = AudioStreamer()
    devices = streamer.list_audio_devices()
    assert isinstance(devices, list)
    assert len(devices) > 0
    assert any("OpenDeskCast" in d for d in devices)


def test_audio_device_manager_routing_cycle():
    mgr = AudioDeviceManager()
    assert mgr._is_routed is False
    mgr.route_audio_to_cast()
    assert mgr._is_routed is True
    mgr.restore_audio()
    assert mgr._is_routed is False


@pytest.mark.anyio
async def test_audio_streamer_subscription():
    streamer = AudioStreamer()
    q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=8)
    streamer.add_subscriber(q, audio_enabled=True)
    try:
        chunk = await asyncio.wait_for(q.get(), timeout=1.5)
        assert isinstance(chunk, bytes)
        assert len(chunk) == CHUNK_BYTES
    finally:
        streamer.remove_subscriber(q)
        assert streamer.device_manager._is_routed is False


@pytest.mark.anyio
async def test_audio_streamer_toggle_and_shutdown():
    streamer = AudioStreamer()
    q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=8)
    streamer.add_subscriber(q, audio_enabled=True)
    assert streamer.device_manager._is_routed is True

    # Host turns audio off
    streamer.on_audio_enabled_changed(False)
    assert streamer.device_manager._is_routed is False

    # Host turns audio back on
    streamer.on_audio_enabled_changed(True)
    assert streamer.device_manager._is_routed is True

    # Shutdown restores audio
    streamer.shutdown()
    assert streamer.device_manager._is_routed is False


def test_receiver_has_no_audio_activation_controls():
    root = Path(__file__).resolve().parent.parent
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    client_js = (root / "static" / "client.js").read_text(encoding="utf-8")
    style_css = (root / "static" / "style.css").read_text(encoding="utf-8")

    assert "unmute-banner" not in index_html
    assert "unmute-banner" not in client_js
    assert "unmute-banner" not in style_css
    assert "Tocca per attivare l'audio" not in index_html

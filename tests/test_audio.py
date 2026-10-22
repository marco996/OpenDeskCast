import asyncio
import pytest
from app.audio import AudioStreamer, CHUNK_BYTES, SAMPLE_RATE


def test_audio_streamer_device_probe():
    streamer = AudioStreamer()
    devices = streamer.list_audio_devices()
    assert isinstance(devices, list)
    assert len(devices) > 0


@pytest.mark.anyio
async def test_audio_streamer_subscription():
    streamer = AudioStreamer()
    q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=8)
    streamer.add_subscriber(q)
    try:
        # Wait up to 1.5s for a chunk to arrive
        chunk = await asyncio.wait_for(q.get(), timeout=1.5)
        assert isinstance(chunk, bytes)
        assert len(chunk) == CHUNK_BYTES
    finally:
        streamer.remove_subscriber(q)


@pytest.mark.anyio
async def test_audio_streamer_async_generator():
    streamer = AudioStreamer()
    count = 0
    async for chunk in streamer.stream_pcm_chunks():
        assert len(chunk) == CHUNK_BYTES
        count += 1
        if count >= 3:
            break
    assert count == 3

from app.audio import AudioStreamer


def test_audio_streamer_device_probe():
    streamer = AudioStreamer()
    devices = streamer.list_audio_devices()
    assert isinstance(devices, list)

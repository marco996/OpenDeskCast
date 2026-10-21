from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import sys
from typing import AsyncIterator

SAMPLE_RATE = 44100
CHANNELS = 1
CHUNK_BYTES = 4096  # ~46ms of 16-bit mono PCM at 44.1kHz


class AudioStreamer:
    """Streams low-latency PCM s16le audio from Windows/Linux/macOS to viewers over WebSocket."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS) -> None:
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self._ffmpeg = shutil.which("ffmpeg") or "ffmpeg"

    def list_audio_devices(self) -> list[str]:
        """List available audio capture devices via ffmpeg across Windows, Linux, and macOS."""
        if not shutil.which(self._ffmpeg):
            return []
        if sys.platform.startswith("linux"):
            return ["default"]
        if sys.platform == "darwin":
            return [":0"]
        try:
            proc = subprocess.run(
                [
                    self._ffmpeg,
                    "-hide_banner",
                    "-list_devices",
                    "true",
                    "-f",
                    "dshow",
                    "-i",
                    "dummy",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            output = (proc.stderr or "") + "\n" + (proc.stdout or "")
        except Exception:
            return []

        devices: list[str] = []
        for line in output.splitlines():
            if "(audio)" in line:
                match = re.search(r'"([^"]+)"', line)
                if match:
                    devices.append(match.group(1))
        return devices

    def pick_preferred_device(self, requested: str | None = None) -> str | None:
        devices = self.list_audio_devices()
        if not devices:
            return None
        if requested and requested in devices:
            return requested
        keywords = ("stereo mix", "missaggio stereo", "loopback", "cable", "what u hear")
        for dev in devices:
            low = dev.lower()
            if any(k in low for k in keywords):
                return dev
        return devices[0]

    async def stream_pcm_chunks(
        self, device_name: str | None = None
    ) -> AsyncIterator[bytes]:
        """Yield raw s16le PCM chunks from the selected audio device."""
        target = self.pick_preferred_device(device_name)
        if not target or not shutil.which(self._ffmpeg):
            return

        if sys.platform.startswith("linux"):
            input_args = ["-f", "pulse", "-i", target]
        elif sys.platform == "darwin":
            input_args = ["-f", "avfoundation", "-i", target]
        else:
            input_args = ["-f", "dshow", "-audio_buffer_size", "30", "-i", f"audio={target}"]

        cmd = [
            self._ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            *input_args,
            "-ac",
            str(self.channels),
            "-ar",
            str(self.sample_rate),
            "-f",
            "s16le",
            "pipe:1",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            assert proc.stdout is not None
            while True:
                chunk = await proc.stdout.read(CHUNK_BYTES)
                if not chunk:
                    break
                yield chunk
        finally:
            if proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass

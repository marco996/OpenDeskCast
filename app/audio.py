from __future__ import annotations

import asyncio
import atexit
import ctypes
from ctypes import wintypes, POINTER, Structure, byref, c_void_p
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import AsyncIterator, Callable, Set

import numpy as np

SAMPLE_RATE = 48000
CHANNELS = 1
CHUNK_FRAMES = 960  # 20ms a 48kHz
CHUNK_BYTES = CHUNK_FRAMES * 2  # 1920 bytes (16-bit mono)

# Windows Core Audio WASAPI COM definitions
if sys.platform == "win32":
    try:
        import comtypes
        import comtypes.client
        from comtypes import GUID, IUnknown, COMMETHOD, HRESULT

        CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
        IID_IMMDeviceEnumerator = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
        IID_IAudioClient = GUID("{1CB9AD4C-DBFA-4c32-B178-C2F568A703B2}")
        IID_IAudioCaptureClient = GUID("{C8ADBD64-E71E-48a0-A4DE-185C395CD317}")
        IID_IAudioEndpointVolume = GUID("{5CDF2C82-841E-4546-9722-0CF74078229A}")

        eRender = 0
        eConsole = 0
        CLSCTX_ALL = 23
        AUDCLNT_SHAREMODE_SHARED = 0
        AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000

        class WAVEFORMATEX(Structure):
            _fields_ = [
                ("wFormatTag", wintypes.WORD),
                ("nChannels", wintypes.WORD),
                ("nSamplesPerSec", wintypes.DWORD),
                ("nAvgBytesPerSec", wintypes.DWORD),
                ("nBlockAlign", wintypes.WORD),
                ("wBitsPerSample", wintypes.WORD),
                ("cbSize", wintypes.WORD),
            ]

        class IMMDevice(IUnknown):
            _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
            _methods_ = [
                COMMETHOD(
                    [],
                    HRESULT,
                    "Activate",
                    (["in"], POINTER(GUID), "iid"),
                    (["in"], wintypes.DWORD, "dwClsCtx"),
                    (["in"], c_void_p, "pActivationParams"),
                    (["out"], POINTER(POINTER(IUnknown)), "ppInterface"),
                ),
            ]

        class IMMDeviceEnumerator(IUnknown):
            _iid_ = IID_IMMDeviceEnumerator
            _methods_ = [
                COMMETHOD([], HRESULT, "EnumAudioEndpoints"),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetDefaultAudioEndpoint",
                    (["in"], wintypes.DWORD, "dataFlow"),
                    (["in"], wintypes.DWORD, "role"),
                    (["out"], POINTER(POINTER(IMMDevice)), "ppEndpoint"),
                ),
            ]

        class IAudioClient(IUnknown):
            _iid_ = IID_IAudioClient
            _methods_ = [
                COMMETHOD(
                    [],
                    HRESULT,
                    "Initialize",
                    (["in"], wintypes.DWORD, "ShareMode"),
                    (["in"], wintypes.DWORD, "StreamFlags"),
                    (["in"], ctypes.c_int64, "hnsBufferDuration"),
                    (["in"], ctypes.c_int64, "hnsPeriodicity"),
                    (["in"], POINTER(WAVEFORMATEX), "pFormat"),
                    (["in"], POINTER(GUID), "AudioSessionGuid"),
                ),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetBufferSize",
                    (["out"], POINTER(wintypes.UINT), "pNumBufferFrames"),
                ),
                COMMETHOD([], HRESULT, "GetStreamLatency"),
                COMMETHOD([], HRESULT, "GetCurrentPadding"),
                COMMETHOD([], HRESULT, "IsFormatSupported"),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetMixFormat",
                    (["out"], POINTER(POINTER(WAVEFORMATEX)), "ppDeviceFormat"),
                ),
                COMMETHOD([], HRESULT, "GetDevicePeriod"),
                COMMETHOD([], HRESULT, "Start"),
                COMMETHOD([], HRESULT, "Stop"),
                COMMETHOD([], HRESULT, "Reset"),
                COMMETHOD([], HRESULT, "SetEventHandle"),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetService",
                    (["in"], POINTER(GUID), "riid"),
                    (["out"], POINTER(POINTER(IUnknown)), "ppv"),
                ),
            ]

        class IAudioCaptureClient(IUnknown):
            _iid_ = IID_IAudioCaptureClient
            _methods_ = [
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetBuffer",
                    (["out"], POINTER(c_void_p), "ppData"),
                    (["out"], POINTER(wintypes.UINT), "pNumFramesToRead"),
                    (["out"], POINTER(wintypes.DWORD), "pdwFlags"),
                    (["out"], POINTER(ctypes.c_uint64), "pu64DevicePosition"),
                    (["out"], POINTER(ctypes.c_uint64), "pu64QPCPosition"),
                ),
                COMMETHOD(
                    [],
                    HRESULT,
                    "ReleaseBuffer",
                    (["in"], wintypes.UINT, "NumFramesRead"),
                ),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetNextPacketSize",
                    (["out"], POINTER(wintypes.UINT), "pNumFramesInNextPacket"),
                ),
            ]

        class IAudioEndpointVolume(IUnknown):
            _iid_ = IID_IAudioEndpointVolume
            _methods_ = [
                COMMETHOD([], HRESULT, "RegisterControlChangeNotify"),
                COMMETHOD([], HRESULT, "UnregisterControlChangeNotify"),
                COMMETHOD([], HRESULT, "GetChannelCount"),
                COMMETHOD([], HRESULT, "SetMasterVolumeLevel"),
                COMMETHOD([], HRESULT, "SetMasterVolumeLevelScalar"),
                COMMETHOD([], HRESULT, "GetMasterVolumeLevel"),
                COMMETHOD([], HRESULT, "GetMasterVolumeLevelScalar"),
                COMMETHOD([], HRESULT, "SetChannelVolumeLevel"),
                COMMETHOD([], HRESULT, "SetChannelVolumeLevelScalar"),
                COMMETHOD([], HRESULT, "GetChannelLevel"),
                COMMETHOD([], HRESULT, "GetChannelLevelScalar"),
                COMMETHOD(
                    [],
                    HRESULT,
                    "SetMute",
                    (["in"], wintypes.BOOL, "bMute"),
                    (["in"], POINTER(GUID), "pguidEventContext"),
                ),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetMute",
                    (["out"], POINTER(wintypes.BOOL), "pbMute"),
                ),
            ]

        _WASAPI_AVAILABLE = True
    except Exception:
        _WASAPI_AVAILABLE = False
else:
    _WASAPI_AVAILABLE = False


class AudioDeviceManager:
    """Manages muting physical PC speakers while casting and restoring them when finished."""

    def __init__(self) -> None:
        self._is_routed = False
        self._orig_mute_state: bool | None = None
        self._linux_module_id: str | None = None
        self._linux_orig_sink: str | None = None
        atexit.register(self.restore_audio)

    def route_audio_to_cast(self) -> None:
        """Silence physical speakers on PC so sound only goes to the cast."""
        if self._is_routed:
            return
        if sys.platform == "win32" and _WASAPI_AVAILABLE:
            try:
                comtypes.CoInitialize()
                enumerator = comtypes.client.CreateObject(
                    CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator
                )
                device = enumerator.GetDefaultAudioEndpoint(eRender, eConsole)
                vol_ptr = device.Activate(byref(IID_IAudioEndpointVolume), CLSCTX_ALL, None)
                vol = vol_ptr.QueryInterface(IAudioEndpointVolume)
                self._orig_mute_state = bool(vol.GetMute())
                vol.SetMute(True, None)
                self._is_routed = True
            except Exception:
                pass
            finally:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass
        elif sys.platform.startswith("linux"):
            try:
                res = subprocess.run(
                    ["pactl", "get-default-sink"], capture_output=True, text=True, timeout=2
                )
                if res.returncode == 0:
                    self._linux_orig_sink = res.stdout.strip()
                load_res = subprocess.run(
                    [
                        "pactl",
                        "load-module",
                        "module-null-sink",
                        "sink_name=OpenDeskCast",
                        'sink_properties=device.description="Audio to OpenDeskCast"',
                    ],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if load_res.returncode == 0:
                    self._linux_module_id = load_res.stdout.strip()
                    subprocess.run(["pactl", "set-default-sink", "OpenDeskCast"], timeout=2)
                    self._is_routed = True
            except Exception:
                pass
        elif sys.platform == "darwin":
            try:
                subprocess.run(["osascript", "-e", "set volume output muted true"], timeout=2)
                self._is_routed = True
            except Exception:
                pass

    def restore_audio(self) -> None:
        """Unmute physical PC speakers so sound is heard locally again."""
        if not self._is_routed:
            return
        self._is_routed = False
        if sys.platform == "win32" and _WASAPI_AVAILABLE:
            try:
                comtypes.CoInitialize()
                enumerator = comtypes.client.CreateObject(
                    CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator
                )
                device = enumerator.GetDefaultAudioEndpoint(eRender, eConsole)
                vol_ptr = device.Activate(byref(IID_IAudioEndpointVolume), CLSCTX_ALL, None)
                vol = vol_ptr.QueryInterface(IAudioEndpointVolume)
                target_mute = self._orig_mute_state if self._orig_mute_state is not None else False
                vol.SetMute(target_mute, None)
            except Exception:
                pass
            finally:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass
        elif sys.platform.startswith("linux"):
            try:
                if self._linux_orig_sink:
                    subprocess.run(["pactl", "set-default-sink", self._linux_orig_sink], timeout=2)
                if self._linux_module_id:
                    subprocess.run(["pactl", "unload-module", self._linux_module_id], timeout=3)
            except Exception:
                pass
        elif sys.platform == "darwin":
            try:
                subprocess.run(["osascript", "-e", "set volume output muted false"], timeout=2)
            except Exception:
                pass


class _WasapiLoopbackWorker(threading.Thread):
    """Background worker capturing default Windows render output using native WASAPI Loopback."""

    def __init__(self, callback: Callable[[bytes], None], sample_rate: int = SAMPLE_RATE) -> None:
        super().__init__(name="WasapiLoopbackWorker", daemon=True)
        self.callback = callback
        self.sample_rate = sample_rate
        self.stop_event = threading.Event()

    def run(self) -> None:
        if not _WASAPI_AVAILABLE:
            self._run_silence_fallback()
            return

        comtypes.CoInitialize()
        try:
            self._capture_loop()
        finally:
            try:
                comtypes.CoUninitialize()
            except Exception:
                pass

    def _capture_loop(self) -> None:
        accum_samples = np.empty(0, dtype=np.int16)
        chunk_frames = CHUNK_FRAMES
        last_packet_time = time.monotonic()

        while not self.stop_event.is_set():
            client = None
            try:
                enumerator = comtypes.client.CreateObject(
                    CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator
                )
                device = enumerator.GetDefaultAudioEndpoint(eRender, eConsole)
                client_ptr = device.Activate(byref(IID_IAudioClient), CLSCTX_ALL, None)
                client = client_ptr.QueryInterface(IAudioClient)

                mix_fmt_ptr = client.GetMixFormat()
                fmt = mix_fmt_ptr.contents
                channels = int(fmt.nChannels)
                rate = int(fmt.nSamplesPerSec)
                bits = int(fmt.wBitsPerSample)

                client.Initialize(
                    AUDCLNT_SHAREMODE_SHARED,
                    AUDCLNT_STREAMFLAGS_LOOPBACK,
                    10000000,
                    0,
                    mix_fmt_ptr,
                    None,
                )
                capture_ptr = client.GetService(byref(IID_IAudioCaptureClient))
                capture_client = capture_ptr.QueryInterface(IAudioCaptureClient)

                client.Start()

                while not self.stop_event.is_set():
                    packet_size = capture_client.GetNextPacketSize()
                    if packet_size > 0:
                        p_data, num_frames, flags, dev_pos, qpc_pos = capture_client.GetBuffer()
                        if num_frames > 0:
                            last_packet_time = time.monotonic()
                            is_silent = bool(flags & 0x02)
                            if is_silent or not p_data:
                                mono_int16 = np.zeros(num_frames, dtype=np.int16)
                            elif bits == 32:
                                raw = ctypes.string_at(p_data, num_frames * channels * 4)
                                arr = np.frombuffer(raw, dtype=np.float32)
                                if channels >= 2:
                                    mono_f32 = (arr[0::channels] + arr[1::channels]) * 0.5
                                else:
                                    mono_f32 = arr
                                mono_int16 = np.clip(
                                    mono_f32 * 32767.0, -32768.0, 32767.0
                                ).astype(np.int16)
                            elif bits == 16:
                                raw = ctypes.string_at(p_data, num_frames * channels * 2)
                                arr = np.frombuffer(raw, dtype=np.int16)
                                if channels >= 2:
                                    mono_i32 = (
                                        arr[0::channels].astype(np.int32)
                                        + arr[1::channels].astype(np.int32)
                                    ) // 2
                                    mono_int16 = mono_i32.astype(np.int16)
                                else:
                                    mono_int16 = arr
                            else:
                                mono_int16 = np.zeros(num_frames, dtype=np.int16)

                            accum_samples = np.concatenate((accum_samples, mono_int16))
                            capture_client.ReleaseBuffer(num_frames)

                            while len(accum_samples) >= chunk_frames:
                                chunk = accum_samples[:chunk_frames].tobytes()
                                accum_samples = accum_samples[chunk_frames:]
                                self.callback(chunk)
                    else:
                        time.sleep(0.005)
                        now = time.monotonic()
                        if now - last_packet_time >= 0.04:
                            last_packet_time = now
                            self.callback(b"\x00" * CHUNK_BYTES)

            except Exception:
                time.sleep(0.2)
                now = time.monotonic()
                if now - last_packet_time >= 0.04:
                    last_packet_time = now
                    self.callback(b"\x00" * CHUNK_BYTES)
            finally:
                if client is not None:
                    try:
                        client.Stop()
                    except Exception:
                        pass

    def _run_silence_fallback(self) -> None:
        silence = b"\x00" * CHUNK_BYTES
        while not self.stop_event.is_set():
            self.callback(silence)
            time.sleep(0.02)

    def stop(self) -> None:
        self.stop_event.set()
        self.join(timeout=1.0)


class _SubprocessAudioWorker(threading.Thread):
    """Background worker capturing audio from Linux (parec/ffmpeg) or macOS (ffmpeg)."""

    def __init__(self, cmd: list[str], callback: Callable[[bytes], None]) -> None:
        super().__init__(name="SubprocessAudioWorker", daemon=True)
        self.cmd = cmd
        self.callback = callback
        self.stop_event = threading.Event()
        self.proc: subprocess.Popen[bytes] | None = None

    def run(self) -> None:
        try:
            self.proc = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=CHUNK_BYTES * 4,
            )
            while not self.stop_event.is_set():
                if self.proc.stdout is None:
                    break
                chunk = self.proc.stdout.read(CHUNK_BYTES)
                if not chunk:
                    break
                self.callback(chunk)
        except Exception:
            silence = b"\x00" * CHUNK_BYTES
            while not self.stop_event.is_set():
                self.callback(silence)
                time.sleep(0.02)
        finally:
            if self.proc:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=0.5)
                except Exception:
                    pass

    def stop(self) -> None:
        self.stop_event.set()
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass
        self.join(timeout=1.0)


class AudioStreamer:
    """Streams low-latency PCM s16le audio across Windows, Linux, and macOS to viewers."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS) -> None:
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self._subscribers: Set[asyncio.Queue[bytes]] = set()
        self._worker: threading.Thread | None = None
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self.device_manager = AudioDeviceManager()
        self._ffmpeg = shutil.which("ffmpeg")

    def _broadcast_chunk(self, chunk: bytes) -> None:
        if not self._subscribers or not self._loop or self._loop.is_closed():
            return

        def _deliver() -> None:
            for q in list(self._subscribers):
                try:
                    if q.full():
                        try:
                            q.get_nowait()
                        except Exception:
                            pass
                    q.put_nowait(chunk)
                except Exception:
                    pass

        try:
            self._loop.call_soon_threadsafe(_deliver)
        except Exception:
            pass

    def _start_worker(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return

        if sys.platform == "win32":
            self._worker = _WasapiLoopbackWorker(self._broadcast_chunk, self.sample_rate)
            self._worker.start()
        elif sys.platform.startswith("linux"):
            parec = shutil.which("parec")
            if parec:
                cmd = [
                    parec,
                    "--format=s16le",
                    f"--rate={self.sample_rate}",
                    f"--channels={self.channels}",
                    "-d",
                    "OpenDeskCast.monitor",
                ]
                self._worker = _SubprocessAudioWorker(cmd, self._broadcast_chunk)
                self._worker.start()
            elif self._ffmpeg:
                cmd = [
                    self._ffmpeg,
                    "-hide_banner",
                    "-f",
                    "pulse",
                    "-i",
                    "OpenDeskCast.monitor",
                    "-ac",
                    str(self.channels),
                    "-ar",
                    str(self.sample_rate),
                    "-f",
                    "s16le",
                    "pipe:1",
                ]
                self._worker = _SubprocessAudioWorker(cmd, self._broadcast_chunk)
                self._worker.start()
            else:
                self._worker = _WasapiLoopbackWorker(self._broadcast_chunk, self.sample_rate)
                self._worker.start()
        elif sys.platform == "darwin":
            if self._ffmpeg:
                cmd = [
                    self._ffmpeg,
                    "-hide_banner",
                    "-f",
                    "avfoundation",
                    "-i",
                    ":0",
                    "-ac",
                    str(self.channels),
                    "-ar",
                    str(self.sample_rate),
                    "-f",
                    "s16le",
                    "pipe:1",
                ]
                self._worker = _SubprocessAudioWorker(cmd, self._broadcast_chunk)
                self._worker.start()
            else:
                self._worker = _WasapiLoopbackWorker(self._broadcast_chunk, self.sample_rate)
                self._worker.start()
        else:
            self._worker = _WasapiLoopbackWorker(self._broadcast_chunk, self.sample_rate)
            self._worker.start()

    def _stop_worker(self) -> None:
        if self._worker is not None:
            if hasattr(self._worker, "stop"):
                self._worker.stop()
            self._worker = None

    def add_subscriber(self, queue: asyncio.Queue[bytes], audio_enabled: bool = True) -> None:
        with self._lock:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            self._subscribers.add(queue)
            if self._worker is None or not self._worker.is_alive():
                self._start_worker()
            if audio_enabled:
                self.device_manager.route_audio_to_cast()

    def remove_subscriber(self, queue: asyncio.Queue[bytes]) -> None:
        with self._lock:
            self._subscribers.discard(queue)
            if not self._subscribers:
                self._stop_worker()
                self.device_manager.restore_audio()

    def on_audio_enabled_changed(self, enabled: bool) -> None:
        with self._lock:
            if enabled and self._subscribers:
                self.device_manager.route_audio_to_cast()
            else:
                self.device_manager.restore_audio()

    def shutdown(self) -> None:
        with self._lock:
            self._subscribers.clear()
            self._stop_worker()
            self.device_manager.restore_audio()

    def list_audio_devices(self) -> list[str]:
        """List available audio capture devices across Windows, Linux, and macOS."""
        devices: list[str] = []
        if sys.platform == "win32":
            if _WASAPI_AVAILABLE:
                devices.append("Audio to OpenDeskCast (Loopback di sistema)")
        elif sys.platform.startswith("linux"):
            devices.append("Audio to OpenDeskCast (Pulse/PipeWire)")
        elif sys.platform == "darwin":
            devices.append("Audio to OpenDeskCast (CoreAudio/AVFoundation)")

        if self._ffmpeg and sys.platform == "win32":
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
                    timeout=3,
                )
                output = (proc.stderr or "") + "\n" + (proc.stdout or "")
                for line in output.splitlines():
                    if "(audio)" in line:
                        match = re.search(r'"([^"]+)"', line)
                        if match and match.group(1) not in devices:
                            devices.append(match.group(1))
            except Exception:
                pass

        if not devices:
            devices.append("Audio to OpenDeskCast")
        return devices

    def pick_preferred_device(self, requested: str | None = None) -> str | None:
        devices = self.list_audio_devices()
        if not devices:
            return None
        if requested and requested in devices:
            return requested
        return devices[0]

    async def stream_pcm_chunks(
        self, device_name: str | None = None
    ) -> AsyncIterator[bytes]:
        """Yield raw s16le PCM chunks from system audio via subscriber queue."""
        q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=16)
        self.add_subscriber(q)
        try:
            while True:
                chunk = await q.get()
                yield chunk
        finally:
            self.remove_subscriber(q)

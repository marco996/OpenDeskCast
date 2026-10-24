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
        IID_IMMDeviceCollection = GUID("{0BD7A1BE-7A1A-44DB-8397-CC5392387B5E}")
        IID_IMMDevice = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
        IID_IPropertyStore = GUID("{886d8eeb-8cf2-4446-8d02-cdba1dbdcf99}")
        IID_IAudioClient = GUID("{1CB9AD4C-DBFA-4c32-B178-C2F568A703B2}")
        IID_IAudioCaptureClient = GUID("{C8ADBD64-E71E-48a0-A4DE-185C395CD317}")
        IID_IAudioEndpointVolume = GUID("{5CDF2C82-841E-4546-9722-0CF74078229A}")

        eRender = 0
        eConsole = 0
        CLSCTX_ALL = 23
        STGM_READ = 0
        DEVICE_STATE_ACTIVE = 0x00000001
        AUDCLNT_SHAREMODE_SHARED = 0
        AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000

        class PROPERTYKEY(Structure):
            _fields_ = [
                ("fmtid", GUID),
                ("pid", wintypes.DWORD),
            ]

        PKEY_Device_FriendlyName = PROPERTYKEY(GUID("{a45c254e-df1c-4efd-8020-67d146a850e0}"), 14)

        class PROPVARIANT(Structure):
            _fields_ = [
                ("vt", ctypes.c_ushort),
                ("wReserved1", wintypes.WORD),
                ("wReserved2", wintypes.WORD),
                ("wReserved3", wintypes.WORD),
                ("pwszVal", wintypes.LPWSTR),
                ("dummy", wintypes.DWORD),
            ]

        class IPropertyStore(IUnknown):
            _iid_ = IID_IPropertyStore
            _methods_ = [
                COMMETHOD([], HRESULT, "GetCount", (["out"], POINTER(wintypes.DWORD), "cProps")),
                COMMETHOD([], HRESULT, "GetAt", (["in"], wintypes.DWORD, "iProp"), (["out"], POINTER(PROPERTYKEY), "pkey")),
                COMMETHOD([], HRESULT, "GetValue", (["in"], POINTER(PROPERTYKEY), "key"), (["out", "retval"], POINTER(PROPVARIANT), "pv")),
                COMMETHOD([], HRESULT, "SetValue"),
                COMMETHOD([], HRESULT, "Commit"),
            ]

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
                COMMETHOD(
                    [],
                    HRESULT,
                    "OpenPropertyStore",
                    (["in"], wintypes.DWORD, "stgmAccess"),
                    (["out"], POINTER(POINTER(IPropertyStore)), "ppProperties"),
                ),
                COMMETHOD([], HRESULT, "GetId", (["out"], POINTER(wintypes.LPWSTR), "ppstrId")),
                COMMETHOD([], HRESULT, "GetState", (["out"], POINTER(wintypes.DWORD), "pdwState")),
            ]

        class IMMDeviceCollection(IUnknown):
            _iid_ = IID_IMMDeviceCollection
            _methods_ = [
                COMMETHOD([], HRESULT, "GetCount", (["out"], POINTER(wintypes.UINT), "pcDevices")),
                COMMETHOD([], HRESULT, "Item", (["in"], wintypes.UINT, "nDevice"), (["out"], POINTER(POINTER(IMMDevice)), "ppDevice")),
            ]

        class IMMDeviceEnumerator(IUnknown):
            _iid_ = IID_IMMDeviceEnumerator
            _methods_ = [
                COMMETHOD(
                    [],
                    HRESULT,
                    "EnumAudioEndpoints",
                    (["in"], wintypes.DWORD, "dataFlow"),
                    (["in"], wintypes.DWORD, "dwStateMask"),
                    (["out"], POINTER(POINTER(IMMDeviceCollection)), "ppDevices"),
                ),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetDefaultAudioEndpoint",
                    (["in"], wintypes.DWORD, "dataFlow"),
                    (["in"], wintypes.DWORD, "role"),
                    (["out"], POINTER(POINTER(IMMDevice)), "ppEndpoint"),
                ),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetDevice",
                    (["in"], wintypes.LPCWSTR, "pwstrId"),
                    (["out"], POINTER(POINTER(IMMDevice)), "ppDevice"),
                ),
            ]

        CLSID_PolicyConfigClient = GUID("{870AF99C-171D-4F9E-AF0D-E63DF40C2BC9}")
        IID_IPolicyConfig = GUID("{F8679F50-850A-41CF-9C72-430F290290C8}")

        class IPolicyConfig(IUnknown):
            _case_insensitive_ = True
            _iid_ = IID_IPolicyConfig
            _methods_ = [
                COMMETHOD([], HRESULT, "GetMixFormat"),
                COMMETHOD([], HRESULT, "GetDeviceFormat"),
                COMMETHOD([], HRESULT, "ResetDeviceFormat"),
                COMMETHOD([], HRESULT, "SetDeviceFormat"),
                COMMETHOD([], HRESULT, "GetProcessingPeriod"),
                COMMETHOD([], HRESULT, "SetProcessingPeriod"),
                COMMETHOD([], HRESULT, "GetShareMode"),
                COMMETHOD([], HRESULT, "SetShareMode"),
                COMMETHOD([], HRESULT, "GetPropertyValue"),
                COMMETHOD([], HRESULT, "SetPropertyValue"),
                COMMETHOD(
                    [],
                    HRESULT,
                    "SetDefaultEndpoint",
                    (["in"], ctypes.c_wchar_p, "wszDeviceId"),
                    (["in"], ctypes.c_ulong, "eRole"),
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
    """Manages audio sink routing on Windows and Linux while keeping PC speakers unmuted."""

    def __init__(self) -> None:
        self._is_routed = False
        self._orig_windows_endpoint: str | None = None
        self._target_cast_endpoint: str | None = None
        self._linux_module_id: str | None = None
        self._linux_orig_sink: str | None = None
        atexit.register(self.restore_audio)

    def get_windows_endpoints(self) -> list[tuple[str, str]]:
        """Return list of (endpoint_id, friendly_name) for all active render endpoints."""
        results: list[tuple[str, str]] = []
        if sys.platform != "win32" or not _WASAPI_AVAILABLE:
            return results
        try:
            comtypes.CoInitialize()
            enumerator = comtypes.client.CreateObject(
                CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator
            )
            col = enumerator.EnumAudioEndpoints(eRender, DEVICE_STATE_ACTIVE)
            count = col.GetCount()
            for i in range(count):
                try:
                    dev = col.Item(i)
                    dev_id = str(dev.GetId())
                    name = f"Audio Endpoint {i+1}"
                    try:
                        props_ptr = dev.OpenPropertyStore(STGM_READ)
                        props = props_ptr.QueryInterface(IPropertyStore)
                        pv = props.GetValue(byref(PKEY_Device_FriendlyName))
                        if pv.vt == 31 and pv.pwszVal:
                            name = str(pv.pwszVal)
                    except Exception:
                        pass
                    results.append((dev_id, name))
                except Exception:
                    pass
        except Exception:
            pass
        return results

    def find_cast_target_endpoint(self) -> tuple[str | None, str | None]:
        """Find dedicated virtual cable or fallback silent endpoint."""
        endpoints = self.get_windows_endpoints()
        # 1. Look for virtual cable (VB-CABLE, Virtual Audio, OpenDeskCast, Steam Streaming)
        for did, name in endpoints:
            nl = name.lower()
            if any(k in nl for k in ("cable input", "vb-audio", "virtual audio", "opendeskcast", "steam streaming")):
                return did, name
        # 2. Look for silent digital/auxiliary output
        for did, name in endpoints:
            nl = name.lower()
            if any(k in nl for k in ("digital output", "s/pdif", "optical")):
                return did, name
        return None, None

    def has_virtual_cable(self) -> bool:
        if sys.platform != "win32":
            return True  # Native null-sink on Linux
        endpoints = self.get_windows_endpoints()
        for _, name in endpoints:
            nl = name.lower()
            if any(k in nl for k in ("cable input", "vb-audio", "virtual audio", "opendeskcast", "steam streaming")):
                return True
        return False

    def route_audio_to_cast(self) -> None:
        if self._is_routed:
            return
        if sys.platform == "win32" and _WASAPI_AVAILABLE:
            try:
                comtypes.CoInitialize()
                enumerator = comtypes.client.CreateObject(
                    CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator
                )
                try:
                    def_dev = enumerator.GetDefaultAudioEndpoint(eRender, eConsole)
                    self._orig_windows_endpoint = str(def_dev.GetId())
                except Exception:
                    self._orig_windows_endpoint = None

                target_id, target_name = self.find_cast_target_endpoint()
                if target_id and target_id != self._orig_windows_endpoint:
                    self._target_cast_endpoint = target_id
                    policy = comtypes.CoCreateInstance(
                        CLSID_PolicyConfigClient,
                        interface=IPolicyConfig,
                        clsctx=comtypes.CLSCTX_INPROC_SERVER,
                    )
                    for role in (0, 1, 2):
                        policy.SetDefaultEndpoint(target_id, role)
                    self._is_routed = True
                else:
                    self._is_routed = True
            except Exception:
                self._is_routed = True
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
                        "sink_properties=device.description=Audio_to_OpenDeskCast",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if load_res.returncode != 0:
                    load_res = subprocess.run(
                        ["pactl", "load-module", "module-null-sink", "sink_name=OpenDeskCast"],
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
                self._is_routed = True

    def restore_audio(self) -> None:
        if not self._is_routed:
            return
        self._is_routed = False
        if sys.platform == "win32" and _WASAPI_AVAILABLE:
            try:
                if self._orig_windows_endpoint:
                    comtypes.CoInitialize()
                    policy = comtypes.CoCreateInstance(
                        CLSID_PolicyConfigClient,
                        interface=IPolicyConfig,
                        clsctx=comtypes.CLSCTX_INPROC_SERVER,
                    )
                    for role in (0, 1, 2):
                        policy.SetDefaultEndpoint(self._orig_windows_endpoint, role)
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
    """Background worker capturing selected Windows render output using native WASAPI Loopback."""

    def __init__(
        self,
        callback: Callable[[bytes], None],
        sample_rate: int = SAMPLE_RATE,
        device_id: str = "default",
    ) -> None:
        super().__init__(name="WasapiLoopbackWorker", daemon=True)
        self.callback = callback
        self.sample_rate = sample_rate
        self.device_id = str(device_id or "default")
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
                if self.device_id and self.device_id != "default":
                    try:
                        device = enumerator.GetDevice(self.device_id)
                    except Exception:
                        device = enumerator.GetDefaultAudioEndpoint(eRender, eConsole)
                else:
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
                    time.sleep(0.02)
                    self.callback(b"\x00" * CHUNK_BYTES)
                    continue
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
        self.device_id = "default"
        self.destination = "speakers"  # "speakers" (local PC) or "cast" (remote)
        self._subscribers: Set[asyncio.Queue[bytes]] = set()
        self._worker: threading.Thread | None = None
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self.device_manager = AudioDeviceManager()
        self._ffmpeg = shutil.which("ffmpeg")

    def set_destination(self, destination: str) -> None:
        with self._lock:
            dest = "speakers" if destination == "speakers" else "cast"
            if self.destination == dest:
                return
            self.destination = dest
            if self.destination == "cast":
                self.device_manager.route_audio_to_cast()
                if self.device_manager._target_cast_endpoint:
                    self.device_id = self.device_manager._target_cast_endpoint
                else:
                    self.device_id = "default"
                if self._worker is not None:
                    self._stop_worker()
                if self._subscribers:
                    self._start_worker()
            else:
                self.device_manager.restore_audio()
                self.device_id = "default"
                if self._worker is not None:
                    self._stop_worker()
                # Flush queues so no leftover speaker audio is played on receiver
                for q in list(self._subscribers):
                    while not q.empty():
                        try:
                            q.get_nowait()
                        except Exception:
                            break

    def set_device(self, device_id: str) -> None:
        # Backward compatibility for endpoints passing device_id
        if device_id in ("speakers", "cast"):
            self.set_destination(device_id)
        else:
            with self._lock:
                did = str(device_id or "default")
                if self.device_id == did:
                    return
                self.device_id = did
                if self._worker is not None:
                    self._stop_worker()
                    if self._subscribers:
                        self._start_worker()

    def _broadcast_chunk(self, chunk: bytes) -> None:
        if not self._subscribers or not self._loop or self._loop.is_closed():
            return
        # If destination is set to local PC speakers, never stream audio to receivers
        if self.destination != "cast":
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
            self._worker = _WasapiLoopbackWorker(self._broadcast_chunk, self.sample_rate, self.device_id)
            self._worker.start()
        elif sys.platform.startswith("linux"):
            parec = shutil.which("parec")
            target_device = self.device_id if self.device_id != "default" else None
            if parec:
                cmd = [
                    parec,
                    "--format=s16le",
                    f"--rate={self.sample_rate}",
                    f"--channels={self.channels}",
                ]
                if target_device:
                    cmd.extend(["-d", f"{target_device}.monitor"])
                self._worker = _SubprocessAudioWorker(cmd, self._broadcast_chunk)
                self._worker.start()
            elif self._ffmpeg:
                cmd = [
                    self._ffmpeg,
                    "-hide_banner",
                    "-f",
                    "pulse",
                    "-i",
                    f"{target_device}.monitor" if target_device else "default",
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
                self._worker = _WasapiLoopbackWorker(self._broadcast_chunk, self.sample_rate, self.device_id)
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
                self._worker = _WasapiLoopbackWorker(self._broadcast_chunk, self.sample_rate, self.device_id)
                self._worker.start()
        else:
            self._worker = _WasapiLoopbackWorker(self._broadcast_chunk, self.sample_rate, self.device_id)
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
            if audio_enabled and self.destination == "cast":
                self.device_manager.route_audio_to_cast()
                if self._worker is None or not self._worker.is_alive():
                    self._start_worker()

    def remove_subscriber(self, queue: asyncio.Queue[bytes]) -> None:
        with self._lock:
            self._subscribers.discard(queue)
            if not self._subscribers:
                self._stop_worker()
                self.device_manager.restore_audio()

    def on_audio_enabled_changed(self, enabled: bool) -> None:
        with self._lock:
            if enabled and self.destination == "cast":
                self.device_manager.route_audio_to_cast()
                if self._subscribers and (self._worker is None or not self._worker.is_alive()):
                    self._start_worker()
            else:
                self.device_manager.restore_audio()
                if self._worker is not None:
                    self._stop_worker()

    def shutdown(self) -> None:
        with self._lock:
            self._subscribers.clear()
            self._stop_worker()
            self.device_manager.restore_audio()

    def list_audio_devices(self, viewers_count: int = 0) -> list[dict[str, str]]:
        """Return the available destinations based on whether a receiver is currently connected."""
        devices = [{"id": "speakers", "name": "Altoparlanti PC (Locale)"}]
        if viewers_count > 0:
            devices.append({"id": "cast", "name": "Dispositivo Ricevente (OpenDeskCast)"})
        return devices

    def pick_preferred_device(self, requested: str | None = None) -> str | None:
        if requested in ("speakers", "cast"):
            return requested
        return "cast"

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


def mark_driver_installed_by_app() -> None:
    """Record that OpenDeskCast initiated the VB-CABLE driver installation."""
    if sys.platform != "win32":
        return
    import os
    from pathlib import Path
    import winreg

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\OpenDeskCast") as key:
            winreg.SetValueEx(key, "DriverInstalledByApp", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

    try:
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            marker_dir = Path(local_app) / "OpenDeskCast"
            marker_dir.mkdir(parents=True, exist_ok=True)
            (marker_dir / ".driver_installed_by_app").write_text("1", encoding="utf-8")
    except Exception:
        pass

    try:
        base_dir = Path(__file__).resolve().parent.parent
        mfile = base_dir / "drivers" / "vbcable" / ".installed_by_opendeskcast"
        if mfile.parent.is_dir():
            mfile.write_text("1", encoding="utf-8")
    except Exception:
        pass


def launch_driver_installer() -> bool:
    """Launch VB-CABLE driver setup with elevated privileges and mark for clean uninstall."""
    if sys.platform != "win32":
        return False
    from pathlib import Path
    base_dir = Path(__file__).resolve().parent.parent
    exe_path = base_dir / "drivers" / "vbcable" / "VBCABLE_Setup_x64.exe"
    if not exe_path.is_file():
        return False
    try:
        mark_driver_installed_by_app()
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Start-Process -FilePath '{exe_path}' -ArgumentList '-i -h' -Verb RunAs",
        ]
        subprocess.Popen(cmd)
        return True
    except Exception:
        return False

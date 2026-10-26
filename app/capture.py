from __future__ import annotations

import atexit
import ctypes
import mmap
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from typing import Any

import cv2
import numpy as np

IS_WIN32 = sys.platform == "win32"


def _is_wayland() -> bool:
    """Return True when running inside a Linux Wayland session (Fedora, Ubuntu Wayland, KDE, Sway, etc.)."""
    if IS_WIN32 or sys.platform == "darwin":
        return False
    return (
        os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"
        or bool(os.environ.get("WAYLAND_DISPLAY"))
    )


def _clean_linux_env() -> dict[str, str]:
    """Return environment stripped of PyInstaller LD_LIBRARY_PATH so system Python/GStreamer works cleanly."""
    env = os.environ.copy()
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env.pop("LD_LIBRARY_PATH_ORIG")
    else:
        env.pop("LD_LIBRARY_PATH", None)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


_WAYLAND_PORTAL_HELPER_SCRIPT = r'''import os
import shutil
import struct
import subprocess
import sys
import time

shm_path = sys.argv[1]
jpg_path = shm_path + ".jpg"

import gi
from gi.repository import GLib, Gio

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
loop = GLib.MainLoop()
pid = os.getpid()

state = {"step": "create", "session_handle": None, "node_id": None}

def call_portal(method, params, reply_type="(o)"):
    return bus.call_sync(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.ScreenCast",
        method,
        params,
        GLib.VariantType(reply_type),
        Gio.DBusCallFlags.NONE,
        -1,
        None,
    )

def start_pipewire_stream(pw_fd, node_id):
    seq = 0
    try:
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        Gst.init(None)
        pipe_str = (
            f"pipewiresrc fd={pw_fd} path={node_id} do-timestamp=true ! "
            f"videoconvert ! video/x-raw,format=BGRx ! "
            f"appsink name=sink emit-signals=true max-buffers=1 drop=true sync=false"
        )
        pipeline = Gst.parse_launch(pipe_str)
        sink = pipeline.get_by_name("sink")

        def on_new_sample(s):
            nonlocal seq
            sample = s.emit("pull-sample")
            if not sample:
                return Gst.FlowReturn.OK
            caps = sample.get_caps()
            st = caps.get_structure(0)
            ok_w, w = st.get_int("width")
            ok_h, h = st.get_int("height")
            if not (ok_w and ok_h and w > 0 and h > 0):
                return Gst.FlowReturn.OK
            buf = sample.get_buffer()
            ok_map, map_info = buf.map(Gst.MapFlags.READ)
            if ok_map:
                try:
                    raw = bytes(map_info.data)
                    stride = len(raw) // h if len(raw) >= w * h * 4 else w * 4
                    seq = (seq + 1) & 0x7FFFFFFF
                    hdr = struct.pack("<IIII", seq, w, h, stride)
                    tmp_path = shm_path + ".tmp"
                    with open(tmp_path, "wb") as f:
                        f.write(hdr)
                        f.write(raw[: stride * h])
                    os.replace(tmp_path, shm_path)
                except Exception:
                    pass
                finally:
                    buf.unmap(map_info)
            return Gst.FlowReturn.OK

        sink.connect("new-sample", on_new_sample)
        pipeline.set_state(Gst.State.PLAYING)
        return
    except Exception:
        pass

    gst_launch = shutil.which("gst-launch-1.0")
    if gst_launch:
        subprocess.Popen(
            [
                gst_launch,
                "-q",
                f"pipewiresrc",
                f"fd={pw_fd}",
                f"path={node_id}",
                "do-timestamp=true",
                "!",
                "videoconvert",
                "!",
                "jpegenc",
                "quality=85",
                "!",
                "multifilesink",
                f"location={jpg_path}",
            ],
            pass_fds=(pw_fd,),
        )

def on_response(conn, sender, obj_path, iface, sig, params):
    code, results = params.unpack()
    if code != 0:
        loop.quit()
        return

    if state["step"] == "create":
        sh = results.get("session_handle")
        if not sh:
            loop.quit()
            return
        state["session_handle"] = sh
        state["step"] = "select"
        opts = {
            "handle_token": GLib.Variant("s", f"odc_sel_{pid}"),
            "types": GLib.Variant("u", 1),
            "multiple": GLib.Variant("b", False),
            "cursor_mode": GLib.Variant("u", 2),
            "persist_mode": GLib.Variant("u", 2),
        }
        try:
            call_portal("SelectSources", GLib.Variant("(oa{sv})", (sh, opts)))
        except Exception:
            loop.quit()

    elif state["step"] == "select":
        state["step"] = "start"
        opts = {"handle_token": GLib.Variant("s", f"odc_start_{pid}")}
        try:
            call_portal("Start", GLib.Variant("(osa{sv})", (state["session_handle"], "", opts)))
        except Exception:
            loop.quit()

    elif state["step"] == "start":
        streams = results.get("streams", [])
        if not streams:
            loop.quit()
            return
        node_id = int(streams[0][0])
        state["node_id"] = node_id
        state["step"] = "streaming"
        try:
            res, fd_list = bus.call_with_unix_fd_list_sync(
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.ScreenCast",
                "OpenPipeWireRemote",
                GLib.Variant("(oa{sv})", (state["session_handle"], {})),
                GLib.VariantType("(h)"),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                None,
            )
            fd_idx = res.unpack()[0]
            pw_fd = fd_list.get(fd_idx)
            start_pipewire_stream(pw_fd, node_id)
        except Exception:
            loop.quit()

bus.signal_subscribe(
    "org.freedesktop.portal.Desktop",
    "org.freedesktop.portal.Request",
    "Response",
    None,
    None,
    Gio.DBusSignalFlags.NONE,
    on_response,
)

create_opts = {
    "handle_token": GLib.Variant("s", f"odc_create_{pid}"),
    "session_handle_token": GLib.Variant("s", f"odc_sess_{pid}"),
}
try:
    call_portal("CreateSession", GLib.Variant("(a{sv})", (create_opts,)))
    loop.run()
except Exception:
    pass
'''


class _WaylandPortalCapturer:
    """Native Wayland screen capturer using XDG Desktop Portal ScreenCast + PipeWire/GStreamer (and grim fallback)."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen[bytes] | None = None
        self._last_start_attempt: float = 0.0
        self._last_frame: np.ndarray | None = None
        shm_dir = Path("/dev/shm") if Path("/dev/shm").is_dir() else Path(tempfile.gettempdir())
        self._shm_path = shm_dir / f"opendeskcast_wl_{os.getpid()}.raw"
        self._jpg_path = Path(str(self._shm_path) + ".jpg")
        self._helper_py_path = shm_dir / f"opendeskcast_wl_helper_{os.getpid()}.py"
        self._grim = shutil.which("grim")
        atexit.register(self.stop)

    def _find_system_python_with_gi(self) -> str | None:
        env = _clean_linux_env()
        candidates = [
            "/usr/bin/python3",
            shutil.which("python3", path=env.get("PATH", "/usr/bin:/bin")),
            sys.executable,
        ]
        for cand in candidates:
            if not cand or not Path(cand).is_file():
                continue
            try:
                res = subprocess.run(
                    [cand, "-c", "import gi; from gi.repository import Gio, GLib"],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                if res.returncode == 0:
                    return cand
            except Exception:
                pass
        return "/usr/bin/python3" if Path("/usr/bin/python3").is_file() else sys.executable

    def start(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        now = time.monotonic()
        if (now - self._last_start_attempt) < 3.0:
            return
        self._last_start_attempt = now
        try:
            self._helper_py_path.write_text(_WAYLAND_PORTAL_HELPER_SCRIPT, encoding="utf-8")
            py_bin = self._find_system_python_with_gi()
            if not py_bin:
                return
            self._proc = subprocess.Popen(
                [py_bin, str(self._helper_py_path), str(self._shm_path)],
                env=_clean_linux_env(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self._proc = None

    def stop(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=0.5)
            except Exception:
                pass
            self._proc = None
        for p in (self._shm_path, Path(str(self._shm_path) + ".tmp"), self._jpg_path, self._helper_py_path):
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

    def _capture_grim(self) -> np.ndarray | None:
        if not self._grim:
            return None
        try:
            res = subprocess.run(
                [self._grim, "-t", "ppm", "-"],
                env=_clean_linux_env(),
                capture_output=True,
                timeout=0.5,
            )
            if res.returncode == 0 and res.stdout:
                arr = np.frombuffer(res.stdout, dtype=np.uint8)
                bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if bgr is not None and bgr.size > 0:
                    return cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
        except Exception:
            pass
        return None

    def _build_waiting_frame(self, width: int, height: int) -> np.ndarray:
        w = max(640, int(width))
        h = max(360, int(height))
        img = np.zeros((h, w, 4), dtype=np.uint8)
        img[:, :, 3] = 255
        cx, cy = w // 2, h // 2
        cv2.rectangle(img, (cx - 380, cy - 95), (cx + 380, cy + 95), (32, 32, 32, 255), -1)
        cv2.rectangle(img, (cx - 380, cy - 95), (cx + 380, cy + 95), (255, 194, 76, 255), 2)
        cv2.putText(
            img,
            "OpenDeskCast - Linux Wayland",
            (cx - 230, cy - 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 194, 76, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            img,
            "Autorizza la condivisione schermo sul PC",
            (cx - 305, cy + 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            (240, 240, 240, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            img,
            "(Seleziona lo schermo e clicca 'Condividi' / 'Share')",
            (cx - 295, cy + 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (170, 170, 170, 255),
            1,
            cv2.LINE_AA,
        )
        return img

    def capture(self, fallback_width: int = 1920, fallback_height: int = 1080) -> np.ndarray:
        # 1. Try grim first on wlroots compositors (Sway/Hyprland) if portal frame not ready
        if not self._shm_path.is_file() and not self._jpg_path.is_file() and self._grim:
            grim_frame = self._capture_grim()
            if grim_frame is not None:
                self._last_frame = grim_frame
                return grim_frame

        # 2. Ensure XDG Portal + PipeWire helper is running
        self.start()

        # 3. Read raw BGRx frame from /dev/shm
        if self._shm_path.is_file():
            try:
                raw_data = self._shm_path.read_bytes()
                if len(raw_data) >= 16:
                    seq, w, h, stride = struct.unpack("<IIII", raw_data[:16])
                    if w > 0 and h > 0 and stride >= w * 4 and len(raw_data) >= 16 + stride * h:
                        rows = np.frombuffer(raw_data, dtype=np.uint8, count=stride * h, offset=16).reshape((h, stride))
                        bgra = rows[:, : w * 4].reshape((h, w, 4)).copy()
                        self._last_frame = bgra
                        return bgra
            except Exception:
                pass

        # 4. Or read JPEG fallback frame if gst-launch-1.0 mode was used
        if self._jpg_path.is_file():
            try:
                jpg_bytes = self._jpg_path.read_bytes()
                if len(jpg_bytes) > 64:
                    arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
                    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if bgr is not None and bgr.size > 0:
                        bgra = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
                        self._last_frame = bgra
                        return bgra
            except Exception:
                pass

        if self._last_frame is not None:
            return self._last_frame

        return self._build_waiting_frame(fallback_width, fallback_height)

if IS_WIN32:
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
else:
    wintypes = None  # type: ignore[assignment]
    user32 = None  # type: ignore[assignment]
    gdi32 = None  # type: ignore[assignment]

SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000
BI_RGB = 0
DIB_RGB_COLORS = 0
CURSOR_SHOWING = 0x00000001
DI_NORMAL = 0x0003
MONITORINFOF_PRIMARY = 0x00000001

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


if IS_WIN32:
    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
            ("szDevice", wintypes.WCHAR * 32),
        ]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [
            ("bmiHeader", BITMAPINFOHEADER),
            ("bmiColors", wintypes.DWORD * 3),
        ]

    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class CURSORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("hCursor", wintypes.HANDLE),
            ("ptScreenPos", POINT),
        ]

    class ICONINFO(ctypes.Structure):
        _fields_ = [
            ("fIcon", wintypes.BOOL),
            ("xHotspot", wintypes.DWORD),
            ("yHotspot", wintypes.DWORD),
            ("hbmMask", wintypes.HBITMAP),
            ("hbmColor", wintypes.HBITMAP),
        ]

    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )


def enable_dpi_awareness() -> None:
    """Enable Per-Monitor V2 DPI awareness (-4) and attach to Default desktop on Windows."""
    if not IS_WIN32:
        return
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
    try:
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            user32.CloseDesktop(hdesk)
    except Exception:
        pass


def get_virtual_screen_bounds() -> tuple[int, int, int, int]:
    """Return (left, top, width, height) of the entire virtual desktop across OSes."""
    if IS_WIN32:
        left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
        top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
        width = max(1, int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)))
        height = max(1, int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)))
        return left, top, width, height

    try:
        import mss  # type: ignore[import-not-found]

        with mss.mss() as sct:
            vbox = sct.monitors[0]
            return (
                int(vbox["left"]),
                int(vbox["top"]),
                max(1, int(vbox["width"])),
                max(1, int(vbox["height"])),
            )
    except Exception:
        return 0, 0, 1920, 1080


def list_monitors() -> list[dict[str, Any]]:
    """Enumerate all active physical monitors across Windows, Linux, and macOS, strictly deduplicated."""
    raw_monitors: list[dict[str, Any]] = []
    seen_rects: set[tuple[int, int, int, int]] = set()

    if IS_WIN32:
        def _callback(hmonitor, hdc, lprect, lparam) -> bool:
            info = MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(MONITORINFOEXW)
            if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                rc = info.rcMonitor
                left = int(rc.left)
                top = int(rc.top)
                width = int(rc.right - rc.left)
                height = int(rc.bottom - rc.top)
                dev = str(info.szDevice).strip()
                rect_key = (left, top, width, height)
                if width > 0 and height > 0 and rect_key not in seen_rects:
                    seen_rects.add(rect_key)
                    raw_monitors.append(
                        {
                            "device": dev,
                            "left": left,
                            "top": top,
                            "width": width,
                            "height": height,
                            "is_primary": bool(info.dwFlags & MONITORINFOF_PRIMARY),
                        }
                    )
            return True

        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_callback), 0)
    else:
        try:
            import mss  # type: ignore[import-not-found]

            with mss.mss() as sct:
                for idx, m in enumerate(sct.monitors[1:]):
                    left = int(m["left"])
                    top = int(m["top"])
                    width = int(m["width"])
                    height = int(m["height"])
                    rect_key = (left, top, width, height)
                    if width > 0 and height > 0 and rect_key not in seen_rects:
                        seen_rects.add(rect_key)
                        raw_monitors.append(
                            {
                                "device": f"DISPLAY{idx + 1}",
                                "left": left,
                                "top": top,
                                "width": width,
                                "height": height,
                                "is_primary": idx == 0,
                            }
                        )
        except Exception:
            pass

    if not raw_monitors:
        vx, vy, vw, vh = get_virtual_screen_bounds()
        raw_monitors.append(
            {
                "device": "\\\\.\\DISPLAY1" if IS_WIN32 else "DISPLAY1",
                "left": vx,
                "top": vy,
                "width": vw,
                "height": vh,
                "is_primary": True,
            }
        )

    raw_monitors.sort(key=lambda m: (not m["is_primary"], m["left"], m["top"]))
    monitors: list[dict[str, Any]] = []
    for idx, mon in enumerate(raw_monitors):
        role = "Principale" if mon["is_primary"] else "Secondario"
        monitors.append(
            {
                "id": idx,
                "name": f"Schermo {idx + 1} ({role} - {mon['width']}x{mon['height']})",
                "device": mon["device"],
                "left": mon["left"],
                "top": mon["top"],
                "width": mon["width"],
                "height": mon["height"],
                "is_primary": mon["is_primary"],
            }
        )
    return monitors


def _draw_cursor_on_dc(mem_dc: int, offset_left: int, offset_top: int) -> None:
    """Draw the active Windows cursor onto the captured memory DC."""
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(CURSORINFO)
    if not user32.GetCursorInfo(ctypes.byref(ci)):
        return
    if not (ci.flags & CURSOR_SHOWING) or not ci.hCursor:
        return

    hotspot_x = 0
    hotspot_y = 0
    ii = ICONINFO()
    if user32.GetIconInfo(ci.hCursor, ctypes.byref(ii)):
        hotspot_x = int(ii.xHotspot)
        hotspot_y = int(ii.yHotspot)
        if ii.hbmMask:
            gdi32.DeleteObject(ii.hbmMask)
        if ii.hbmColor:
            gdi32.DeleteObject(ii.hbmColor)

    draw_x = int(ci.ptScreenPos.x) - offset_left - hotspot_x
    draw_y = int(ci.ptScreenPos.y) - offset_top - hotspot_y
    user32.DrawIconEx(mem_dc, draw_x, draw_y, ci.hCursor, 0, 0, 0, None, DI_NORMAL)


class ScreenCapturer:
    """Ultra-low-latency Win32 GDI / Linux X11 & Wayland PipeWire / macOS screen capturer with delta bounding-box encoding."""

    def __init__(self, keyframe_interval: float = 0.5) -> None:
        enable_dpi_awareness()
        self.keyframe_interval = float(keyframe_interval)
        self._last_monitor_id: int | None = None
        self._last_sent_time: float = 0.0
        self._last_full_time: float = 0.0
        self._cached_monitors: list[dict[str, Any]] = []
        self._monitors_ts: float = 0.0
        self._buf: np.ndarray | None = None
        self._prev_bgr: np.ndarray | None = None
        self._mem_dc: int = 0
        self._hbitmap: int = 0
        self._old_obj: int = 0
        self._dc_size: tuple[int, int] = (0, 0)
        self._wayland_capturer: _WaylandPortalCapturer | None = (
            _WaylandPortalCapturer() if _is_wayland() else None
        )
        self._wayland_force_portal: bool = _is_wayland()

    def warmup(self) -> None:
        """Pre-start Wayland ScreenCast Portal session on Linux Wayland so the permission prompt appears immediately."""
        if _is_wayland():
            if self._wayland_capturer is None:
                self._wayland_capturer = _WaylandPortalCapturer()
            self._wayland_force_portal = True
            self._wayland_capturer.start()

    def _release_gdi_cache(self) -> None:
        if not IS_WIN32:
            return
        if self._old_obj and self._mem_dc:
            try:
                gdi32.SelectObject(self._mem_dc, self._old_obj)
            except Exception:
                pass
            self._old_obj = 0
        if self._hbitmap:
            try:
                gdi32.DeleteObject(self._hbitmap)
            except Exception:
                pass
            self._hbitmap = 0
        if self._mem_dc:
            try:
                gdi32.DeleteDC(self._mem_dc)
            except Exception:
                pass
            self._mem_dc = 0
        self._dc_size = (0, 0)

    def __del__(self) -> None:
        self._release_gdi_cache()
        if getattr(self, "_wayland_capturer", None) is not None:
            try:
                self._wayland_capturer.stop()  # type: ignore[union-attr]
            except Exception:
                pass

    def _resolve_monitor(self, monitor_id: int) -> dict[str, Any]:
        now = time.monotonic()
        if not self._cached_monitors or (now - self._monitors_ts) > 1.0:
            self._cached_monitors = list_monitors()
            self._monitors_ts = now
        for mon in self._cached_monitors:
            if mon["id"] == monitor_id:
                return mon
        return self._cached_monitors[0]

    def capture_raw(
        self, monitor_id: int = 0, draw_cursor: bool = True
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Capture BGRA numpy array of shape (H, W, 4) for the requested monitor across OSes."""
        mon = self._resolve_monitor(monitor_id)
        left, top, width, height = mon["left"], mon["top"], mon["width"], mon["height"]

        if not IS_WIN32:
            if _is_wayland() and self._wayland_force_portal:
                if self._wayland_capturer is None:
                    self._wayland_capturer = _WaylandPortalCapturer()
                bgra = self._wayland_capturer.capture(width, height)
                mon = dict(mon)
                mon["height"], mon["width"] = int(bgra.shape[0]), int(bgra.shape[1])
                return bgra, mon

            try:
                import mss  # type: ignore[import-not-found]

                with mss.mss() as sct:
                    shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
                    arr = np.asarray(shot, dtype=np.uint8)
                    if _is_wayland() and not np.any(arr[:, :, :3]):
                        self._wayland_force_portal = True
                        if self._wayland_capturer is None:
                            self._wayland_capturer = _WaylandPortalCapturer()
                        bgra = self._wayland_capturer.capture(width, height)
                        mon = dict(mon)
                        mon["height"], mon["width"] = int(bgra.shape[0]), int(bgra.shape[1])
                        return bgra, mon
                    return arr, mon
            except Exception:
                if sys.platform.startswith("linux"):
                    self._wayland_force_portal = True
                    if self._wayland_capturer is None:
                        self._wayland_capturer = _WaylandPortalCapturer()
                    bgra = self._wayland_capturer.capture(width, height)
                    mon = dict(mon)
                    mon["height"], mon["width"] = int(bgra.shape[0]), int(bgra.shape[1])
                    return bgra, mon

                from PIL import ImageGrab

                img = ImageGrab.grab(bbox=(left, top, left + width, top + height))
                rgba = np.asarray(img.convert("RGBA"), dtype=np.uint8)
                bgra = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
                return bgra, mon

        hwnd_dc = user32.GetDC(0)
        if not hwnd_dc:
            raise RuntimeError("Impossibile acquisire il Device Context del desktop.")

        try:
            if not self._mem_dc or not self._hbitmap or self._dc_size != (width, height):
                self._release_gdi_cache()
                self._mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
                if not self._mem_dc:
                    raise RuntimeError("CreateCompatibleDC fallito.")
                self._hbitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
                if not self._hbitmap:
                    self._release_gdi_cache()
                    raise RuntimeError("CreateCompatibleBitmap fallito.")
                self._old_obj = gdi32.SelectObject(self._mem_dc, self._hbitmap)
                self._dc_size = (width, height)

            gdi32.BitBlt(
                self._mem_dc,
                0,
                0,
                width,
                height,
                hwnd_dc,
                left,
                top,
                SRCCOPY,
            )

            if draw_cursor:
                _draw_cursor_on_dc(self._mem_dc, left, top)

            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = width
            bmi.bmiHeader.biHeight = -height
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = BI_RGB

            if self._buf is None or self._buf.shape != (height, width, 4):
                self._buf = np.empty((height, width, 4), dtype=np.uint8)
            lines = gdi32.GetDIBits(
                self._mem_dc,
                self._hbitmap,
                0,
                height,
                self._buf.ctypes.data_as(ctypes.c_void_p),
                ctypes.byref(bmi),
                DIB_RGB_COLORS,
            )
            if lines != height:
                raise RuntimeError(f"GetDIBits ha restituito {lines} righe invece di {height}.")
            return self._buf, mon
        finally:
            user32.ReleaseDC(0, hwnd_dc)

    def encode_frame(
        self,
        monitor_id: int = 0,
        quality: int = 75,
        scale: float = 1.0,
        force: bool = False,
        draw_cursor: bool = True,
    ) -> bytes | None:
        """
        Capture and JPEG-encode either the full monitor or the changed bounding-box patch.
        8-byte header (<HHHH): (canvas_w, canvas_h, patch_x, patch_y).
        """
        quality_clamped = max(20, min(100, int(quality)))
        scale_clamped = max(0.25, min(1.0, float(scale)))

        bgra, mon = self.capture_raw(monitor_id=monitor_id, draw_cursor=draw_cursor)
        now = time.monotonic()

        if scale_clamped < 0.99:
            target_w = max(64, int(round(mon["width"] * scale_clamped)))
            target_h = max(64, int(round(mon["height"] * scale_clamped)))
            interp = cv2.INTER_NEAREST if scale_clamped <= 0.65 else cv2.INTER_LINEAR
            resized = cv2.resize(bgra, (target_w, target_h), interpolation=interp)
            bgr = cv2.cvtColor(resized, cv2.COLOR_BGRA2BGR)
        else:
            target_w = int(mon["width"])
            target_h = int(mon["height"])
            bgr = cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)

        need_full = (
            force
            or self._last_monitor_id != mon["id"]
            or self._prev_bgr is None
            or self._prev_bgr.shape != bgr.shape
            or (now - self._last_full_time) >= 2.0
        )

        patch_x = 0
        patch_y = 0
        encode_view = bgr

        if not need_full and self._prev_bgr is not None:
            grid_cur = bgr[::8, ::8]
            grid_prev = self._prev_bgr[::8, ::8]
            diff_mask = np.any(grid_cur != grid_prev, axis=2)
            if not np.any(diff_mask):
                if (now - self._last_sent_time) < self.keyframe_interval:
                    return None
                need_full = True
            else:
                ys, xs = np.nonzero(diff_mask)
                y0 = max(0, (int(ys.min()) - 1) * 8)
                y1 = min(target_h, (int(ys.max()) + 2) * 8)
                x0 = max(0, (int(xs.min()) - 1) * 8)
                x1 = min(target_w, (int(xs.max()) + 2) * 8)
                if (x1 - x0) * (y1 - y0) < int(0.65 * target_w * target_h):
                    patch_x = x0
                    patch_y = y0
                    encode_view = bgr[y0:y1, x0:x1]
                    self._prev_bgr[y0:y1, x0:x1] = encode_view
                else:
                    need_full = True

        if need_full:
            self._prev_bgr = bgr.copy()
            self._last_full_time = now
            patch_x = 0
            patch_y = 0
            encode_view = bgr

        self._last_monitor_id = mon["id"]
        self._last_sent_time = now

        jpeg_params = [
            int(cv2.IMWRITE_JPEG_QUALITY),
            quality_clamped,
            int(cv2.IMWRITE_JPEG_OPTIMIZE),
            0,
        ]
        if quality_clamped >= 100 and hasattr(cv2, "IMWRITE_JPEG_SAMPLING_FACTOR"):
            jpeg_params.extend(
                [
                    int(cv2.IMWRITE_JPEG_SAMPLING_FACTOR),
                    int(getattr(cv2, "IMWRITE_JPEG_SAMPLING_FACTOR_444", 0x111111)),
                ]
            )

        ok, encoded = cv2.imencode(".jpg", encode_view, jpeg_params)
        if not ok:
            raise RuntimeError("Codifica JPEG fallita.")

        header = struct.pack("<HHHH", target_w, target_h, patch_x, patch_y)
        return header + encoded.tobytes()

    def encode_black_frame(self, monitor_id: int = 0, scale: float = 1.0) -> bytes:
        """Encode a full black frame for the given monitor to preserve privacy when sharing is paused."""
        mon = self._resolve_monitor(monitor_id)
        scale_clamped = max(0.25, min(1.0, float(scale)))
        target_w = max(64, int(round(mon["width"] * scale_clamped))) if scale_clamped < 0.99 else int(mon["width"])
        target_h = max(64, int(round(mon["height"] * scale_clamped))) if scale_clamped < 0.99 else int(mon["height"])
        black_img = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", black_img, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        if not ok:
            return b""
        header = struct.pack("<HHHH", target_w, target_h, 0, 0)
        self._prev_bgr = None
        return header + encoded.tobytes()

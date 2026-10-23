from __future__ import annotations

import ctypes
import struct
import sys
import time
from typing import Any

import cv2
import numpy as np

IS_WIN32 = sys.platform == "win32"

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
    """Ultra-low-latency Win32 GDI screen capturer with persistent HBITMAP and delta bounding-box encoding."""

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
            try:
                import mss  # type: ignore[import-not-found]

                with mss.mss() as sct:
                    shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
                    return np.asarray(shot, dtype=np.uint8), mon
            except Exception:
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

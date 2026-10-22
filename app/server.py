from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
import os
from pathlib import Path
import secrets
import signal
import socket
import sys
import time
from typing import Any, Callable

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.audio import AudioStreamer
from app.capture import ScreenCapturer, enable_dpi_awareness, list_monitors
from app.qr_svg import generate_qr_matrix, generate_qr_svg

enable_dpi_awareness()


def _resolve_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def _resolve_static_dir() -> Path:
    return _resolve_base_dir() / "static"


def _resolve_version() -> str:
    vfile = _resolve_base_dir() / "VERSION"
    if vfile.is_file():
        return vfile.read_text(encoding="utf-8").strip() or "1.0.0"
    return "1.0.0"


STATIC_DIR = _resolve_static_dir()
APP_VERSION = _resolve_version()
DEFAULT_PORT = 8765


def _new_token() -> str:
    return secrets.token_urlsafe(8)


def _new_pin() -> str:
    return f"{secrets.randbelow(9000) + 1000:04d}"


@dataclass
class HostState:
    monitor_id: int = 0
    fps: int = 30
    quality: int = 80
    scale: float = 1.0
    draw_cursor: bool = True
    audio_enabled: bool = True
    lock_new_viewers: bool = False
    session_token: str = field(default_factory=_new_token)
    session_pin: str = field(default_factory=_new_pin)
    version: int = 1


class HostSettingsUpdate(BaseModel):
    monitor_id: int | None = None
    fps: int | None = None
    quality: int | None = None
    scale: float | None = None
    draw_cursor: bool | None = None
    audio_enabled: bool | None = None
    lock_new_viewers: bool | None = None


class PinVerifyRequest(BaseModel):
    pin: str


app = FastAPI(title="OpenDeskCast PC Host Server", version=APP_VERSION)
host_state = HostState()
audio_streamer = AudioStreamer()
active_viewers: set[WebSocket] = set()
active_audio_ws: set[WebSocket] = set()
shutdown_callback: Callable[[], None] | None = None
_close_timer_task: asyncio.Task[None] | None = None


@app.middleware("http")
async def disable_browser_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


def _is_localhost(client_host: str | None) -> bool:
    if not client_host:
        return False
    return client_host in {"127.0.0.1", "::1", "localhost"}


def _require_localhost(request: Request) -> None:
    client_host = request.client.host if request.client else None
    if not _is_localhost(client_host):
        raise HTTPException(
            status_code=403,
            detail="Accesso riservato esclusivamente al PC che trasmette (localhost).",
        )


def _is_valid_token(token: str | None) -> bool:
    if not token or not isinstance(token, str):
        return False
    return secrets.compare_digest(token, host_state.session_token)


def _cancel_pending_close_timer() -> None:
    global _close_timer_task
    if _close_timer_task is not None and not _close_timer_task.done():
        _close_timer_task.cancel()
        _close_timer_task = None


def get_local_ipv4_addresses() -> list[str]:
    """Discover all active LAN / Wi-Fi / USB-tethering IPv4 addresses of this PC."""
    ips: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            if primary_ip and not primary_ip.startswith("127."):
                ips.append(primary_ip)
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = str(info[4][0])
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                if ip not in ips:
                    ips.append(ip)
    except Exception:
        pass

    if not ips:
        ips.append("127.0.0.1")
    return ips


async def disconnect_all_viewers(reason: str = "SESSION_TERMINATED") -> None:
    """Permanently disconnect all connected viewers and rotate both session token and 4-digit PIN."""
    host_state.session_token = _new_token()
    host_state.session_pin = _new_pin()
    for ws in list(active_viewers):
        try:
            await ws.close(code=4000, reason=reason)
        except Exception:
            pass
    active_viewers.clear()

    for ws in list(active_audio_ws):
        try:
            await ws.close(code=4000, reason=reason)
        except Exception:
            pass
    active_audio_ws.clear()


async def cleanup_all() -> None:
    """Disconnect all viewers, restore audio, and invalidate token on application exit."""
    audio_streamer.shutdown()
    await disconnect_all_viewers("SESSION_TERMINATED")


@app.get("/api/status")
def api_status(request: Request, port: int = Query(default=DEFAULT_PORT)) -> dict[str, Any]:
    _require_localhost(request)
    _cancel_pending_close_timer()
    ips = get_local_ipv4_addresses()
    tok = host_state.session_token
    urls = [f"http://{ip}:{port}/?t={tok}" for ip in ips]
    return {
        "app_version": APP_VERSION,
        "ips": ips,
        "port": port,
        "urls": urls,
        "base_url": f"http://{ips[0]}:{port}",
        "session_pin": host_state.session_pin,
        "monitors": list_monitors(),
        "settings": asdict(host_state),
        "connected_viewers": len(active_viewers),
    }


@app.post("/api/settings")
def api_update_settings(request: Request, req: HostSettingsUpdate) -> dict[str, Any]:
    _require_localhost(request)
    _cancel_pending_close_timer()
    if req.monitor_id is not None:
        host_state.monitor_id = max(0, int(req.monitor_id))
    if req.fps is not None:
        host_state.fps = max(5, min(60, int(req.fps)))
    if req.quality is not None:
        host_state.quality = max(20, min(100, int(req.quality)))
    if req.scale is not None:
        host_state.scale = max(0.25, min(1.0, float(req.scale)))
    if req.draw_cursor is not None:
        host_state.draw_cursor = bool(req.draw_cursor)
    if req.audio_enabled is not None:
        host_state.audio_enabled = bool(req.audio_enabled)
        audio_streamer.on_audio_enabled_changed(host_state.audio_enabled)
    if req.lock_new_viewers is not None:
        host_state.lock_new_viewers = bool(req.lock_new_viewers)
    host_state.version += 1
    return {"ok": True, "settings": asdict(host_state)}


@app.post("/api/rotate-token")
async def api_rotate_token(request: Request) -> dict[str, Any]:
    """Generate a brand new session token and 4-digit PIN and disconnect all currently connected viewers."""
    _require_localhost(request)
    _cancel_pending_close_timer()
    await disconnect_all_viewers("TOKEN_ROTATED")
    return {
        "ok": True,
        "session_token": host_state.session_token,
        "session_pin": host_state.session_pin,
    }


@app.post("/api/verify-pin")
def api_verify_pin(req: PinVerifyRequest) -> dict[str, Any]:
    """Exchange a valid 4-digit PIN for the active session token (for camera-less viewers)."""
    if host_state.lock_new_viewers:
        raise HTTPException(status_code=403, detail="Nuovi collegamenti bloccati dal PC.")
    candidate = (req.pin or "").strip()
    if len(candidate) != 4 or not secrets.compare_digest(candidate, host_state.session_pin):
        raise HTTPException(status_code=403, detail="PIN non valido.")
    return {"ok": True, "token": host_state.session_token}


@app.post("/api/heartbeat")
def api_heartbeat(request: Request) -> dict[str, Any]:
    _require_localhost(request)
    _cancel_pending_close_timer()
    return {"ok": True, "connected_viewers": len(active_viewers)}


@app.post("/api/window-closed")
async def api_window_closed(request: Request) -> dict[str, Any]:
    global _close_timer_task
    _require_localhost(request)

    async def _delayed_shutdown() -> None:
        await asyncio.sleep(1.5)
        await cleanup_all()
        if shutdown_callback is not None:
            shutdown_callback()
        else:
            os.kill(os.getpid(), signal.SIGTERM)

    if _close_timer_task is None or _close_timer_task.done():
        _close_timer_task = asyncio.create_task(_delayed_shutdown())
    return {"ok": True}


@app.post("/api/shutdown")
async def api_shutdown(request: Request) -> dict[str, Any]:
    _require_localhost(request)
    _cancel_pending_close_timer()
    await cleanup_all()
    if shutdown_callback is not None:
        shutdown_callback()
    else:
        asyncio.get_running_loop().call_later(0.3, lambda: os.kill(os.getpid(), signal.SIGTERM))
    return {"ok": True, "status": "shutting_down"}


@app.get("/api/qr.svg")
def api_qr_svg(request: Request, url: str = Query(..., min_length=1, max_length=120)) -> Response:
    _require_localhost(request)
    svg = generate_qr_svg(url)
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/api/qr.png")
def api_qr_png(request: Request, url: str = Query(..., min_length=1, max_length=120)) -> Response:
    _require_localhost(request)
    mat = np.array(generate_qr_matrix(url, border=3), dtype=np.uint8)
    img = (1 - mat) * 255
    img_scaled = cv2.resize(img, (156, 156), interpolation=cv2.INTER_NEAREST)
    ok, png = cv2.imencode(".png", img_scaled)
    if not ok:
        raise HTTPException(status_code=500, detail="Impossibile generare PNG QR.")
    return Response(content=png.tobytes(), media_type="image/png")


@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket, t: str | None = Query(default=None)) -> None:
    """
    Authenticated Passive HDMI-like Viewer WebSocket with adaptive client-paced flow control.
    Prevents TCP bufferbloat on slower tablets while maintaining 60 FPS on fast devices.
    """
    await ws.accept()
    if not _is_valid_token(t) or host_state.lock_new_viewers:
        await ws.close(code=4003, reason="UNAUTHORIZED")
        return

    active_viewers.add(ws)
    capturer = ScreenCapturer(keyframe_interval=0.5)
    seen_version = -1
    credits = 1
    credit_event = asyncio.Event()
    credit_event.set()

    async def _ack_reader() -> None:
        nonlocal credits
        try:
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                credits = 1
                credit_event.set()
        except Exception:
            pass

    ack_task = asyncio.create_task(_ack_reader())

    try:
        while True:
            if credits <= 0:
                credit_event.clear()
                try:
                    await asyncio.wait_for(credit_event.wait(), timeout=0.08)
                except asyncio.TimeoutError:
                    credits = 1

            t_start = time.monotonic()
            force_next = seen_version != host_state.version
            seen_version = host_state.version

            try:
                packet = await asyncio.to_thread(
                    capturer.encode_frame,
                    monitor_id=host_state.monitor_id,
                    quality=host_state.quality,
                    scale=host_state.scale,
                    force=force_next,
                    draw_cursor=host_state.draw_cursor,
                )
            except Exception:
                packet = None

            if packet is not None:
                credits -= 1
                await ws.send_bytes(packet)

            interval = 1.0 / float(max(5, host_state.fps))
            elapsed = time.monotonic() - t_start
            sleep_sec = max(0.002, interval - elapsed)
            await asyncio.sleep(sleep_sec)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ack_task.cancel()
        active_viewers.discard(ws)


@app.websocket("/ws/audio")
async def ws_audio(ws: WebSocket, t: str | None = Query(default=None)) -> None:
    await ws.accept()
    if not _is_valid_token(t) or host_state.lock_new_viewers:
        await ws.close(code=4003, reason="UNAUTHORIZED")
        return

    active_audio_ws.add(ws)
    queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=16)
    audio_streamer.add_subscriber(queue, audio_enabled=host_state.audio_enabled)
    try:
        while True:
            chunk = await queue.get()
            if host_state.audio_enabled:
                await ws.send_bytes(chunk)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        audio_streamer.remove_subscriber(queue)
        active_audio_ws.discard(ws)


@app.get("/", response_model=None)
def serve_viewer(t: str | None = Query(default=None)) -> Response:
    if host_state.lock_new_viewers or (t is not None and not _is_valid_token(t)):
        return HTMLResponse(
            content='<!DOCTYPE html><html><head><meta charset="utf-8"><title>OpenDeskCast</title></head>'
            '<body style="margin:0;background:#000;color:#000;overflow:hidden;"></body></html>',
            status_code=403,
        )
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin")
def serve_admin(request: Request) -> FileResponse:
    _require_localhost(request)
    _cancel_pending_close_timer()
    return FileResponse(STATIC_DIR / "admin.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

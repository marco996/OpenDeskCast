"""
Wayland screen capture for OpenDeskCast via xdg-desktop-portal (ScreenCast) + PipeWire + GStreamer.

Flow: CreateSession -> SelectSources -> Start (GNOME/KDE share dialog) -> OpenPipeWireRemote
      -> GStreamer "pipewiresrc ! videoconvert ! BGRx ! appsink" -> latest frame kept in memory.

A single process-wide session is shared by every viewer (singleton), so the share dialog
appears once. With persist_mode=2 the restore token is saved and later runs skip the dialog.
"""
from __future__ import annotations

import os
from pathlib import Path
import secrets
import threading
import time

import numpy as np

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SC_IFACE = "org.freedesktop.portal.ScreenCast"
REQ_IFACE = "org.freedesktop.portal.Request"

SOURCE_MONITOR = 1
CURSOR_HIDDEN, CURSOR_EMBEDDED = 1, 2
PERSIST_UNTIL_REVOKED = 2

TOKEN_FILE = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "opendeskcast" / "portal_restore_token"
DIALOG_TIMEOUT_S = 180.0


def is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))


class PortalError(RuntimeError):
    pass


class WaylandScreenCast:
    """Process-wide ScreenCast session; call get_frame() from any thread."""

    _instance: "WaylandScreenCast | None" = None
    _instance_lock = threading.Lock()

    @classmethod
    def get(cls) -> "WaylandScreenCast":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._frame_ts = 0.0
        self._thread: threading.Thread | None = None
        self._running = False
        self._error: str | None = None
        self._pipeline = None
        # The portal closes the session (and GNOME destroys the PipeWire node) as soon as the
        # client's D-Bus connection goes away, so the connection must live as long as the capture.
        self._bus = None
        self._session: str | None = None

    # ------------------------------------------------------------------ public
    def get_frame(self, timeout: float = DIALOG_TIMEOUT_S) -> np.ndarray:
        """Return a BGRA (H, W, 4) uint8 copy of the most recent frame, starting the session if needed."""
        self._ensure_started()
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                if self._frame is not None:
                    return self._frame.copy()
                err = self._error
            if err:
                raise PortalError(err)
            if time.monotonic() > deadline:
                raise PortalError("Nessun frame ricevuto da PipeWire (condivisione non accettata?)")
            time.sleep(0.02)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None
        self._close_session()

    def _close_session(self) -> None:
        bus, session = self._bus, self._session
        self._session = None
        if bus is not None and session:
            try:
                from gi.repository import Gio

                bus.call_sync(
                    PORTAL_BUS, session, "org.freedesktop.portal.Session", "Close",
                    None, None, Gio.DBusCallFlags.NONE, 2000, None,
                )
            except Exception:
                pass

    # ----------------------------------------------------------------- internals
    def _ensure_started(self) -> None:
        with self._lock:
            alive = self._thread is not None and self._thread.is_alive()
            if alive:
                return
            # (re)start after first use or after the user stopped sharing from the GNOME indicator
            self._frame = None
            self._error = None
            self._running = True
            self._thread = threading.Thread(target=self._worker, name="wayland-screencast", daemon=True)
            self._thread.start()

    def _set_error(self, msg: str) -> None:
        with self._lock:
            self._error = msg
        print(f"[wayland_capture] {msg}", flush=True)

    def _worker(self) -> None:
        try:
            fd, node_id = self._portal_handshake()
            try:
                for attempt in range(1, 6):
                    try:
                        self._run_pipeline(os.dup(fd), node_id)
                        break
                    except PortalError as exc:
                        if "target not found" in str(exc) and attempt < 5 and self._running:
                            print(f"[wayland_capture] nodo {node_id} non ancora visibile, riprovo ({attempt}/5)", flush=True)
                            time.sleep(0.5 * attempt)
                            continue
                        raise
            finally:
                try:
                    os.close(fd)
                except OSError:
                    pass
        except Exception as exc:  # surfaced to get_frame()
            self._set_error(f"{type(exc).__name__}: {exc}")
            self._close_session()
        finally:
            self._running = False

    # --- D-Bus portal -------------------------------------------------------
    def _portal_handshake(self) -> tuple[int, int]:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib

        ctx = GLib.MainContext.new()
        ctx.push_thread_default()
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self._bus = bus  # keep a strong reference: dropping it closes the portal session
            sender = bus.get_unique_name()[1:].replace(".", "_")

            def prop(name: str):
                res = bus.call_sync(
                    PORTAL_BUS, PORTAL_PATH, "org.freedesktop.DBus.Properties", "Get",
                    GLib.Variant("(ss)", (SC_IFACE, name)), GLib.VariantType("(v)"),
                    Gio.DBusCallFlags.NONE, -1, None,
                )
                return res.unpack()[0]

            version = int(prop("version"))
            cursor_modes = int(prop("AvailableCursorModes"))

            def request(method: str, signature: str, args: tuple, options: dict, timeout: float) -> dict:
                token = "odc" + secrets.token_hex(6)
                options = dict(options)
                options["handle_token"] = GLib.Variant("s", token)
                req_path = f"{PORTAL_PATH}/request/{sender}/{token}"
                result: dict = {}

                def on_response(_conn, _snd, _path, _iface, _sig, params):
                    code, results = params.unpack()
                    result["code"] = code
                    result["results"] = results

                sub = bus.signal_subscribe(
                    PORTAL_BUS, REQ_IFACE, "Response", req_path, None,
                    Gio.DBusSignalFlags.NONE, on_response,
                )
                try:
                    bus.call_sync(
                        PORTAL_BUS, PORTAL_PATH, SC_IFACE, method,
                        GLib.Variant(signature, (*args, options)), GLib.VariantType("(o)"),
                        Gio.DBusCallFlags.NONE, -1, None,
                    )
                    deadline = time.monotonic() + timeout
                    while "code" not in result:
                        if not self._running:
                            raise PortalError("interrotto")
                        if time.monotonic() > deadline:
                            raise PortalError(f"{method}: timeout in attesa della risposta del portale")
                        ctx.iteration(False) or time.sleep(0.01)
                finally:
                    bus.signal_unsubscribe(sub)
                if result["code"] != 0:
                    reason = {1: "annullato dall'utente", 2: "errore del portale"}.get(result["code"], str(result["code"]))
                    raise PortalError(f"{method}: {reason}")
                return result["results"]

            res = request("CreateSession", "(a{sv})", (), {
                "session_handle_token": GLib.Variant("s", "odcs" + secrets.token_hex(6)),
            }, 30)
            session = res["session_handle"]
            self._session = session

            sel = {
                "types": GLib.Variant("u", SOURCE_MONITOR),
                "multiple": GLib.Variant("b", False),
            }
            if cursor_modes & CURSOR_EMBEDDED:
                sel["cursor_mode"] = GLib.Variant("u", CURSOR_EMBEDDED)
            if version >= 4:
                sel["persist_mode"] = GLib.Variant("u", PERSIST_UNTIL_REVOKED)
                saved = self._load_token()
                if saved:
                    sel["restore_token"] = GLib.Variant("s", saved)
            request("SelectSources", "(oa{sv})", (session,), sel, 30)

            res = request("Start", "(osa{sv})", (session, ""), {}, DIALOG_TIMEOUT_S)
            streams = res.get("streams") or []
            if not streams:
                raise PortalError("Start: nessuno stream restituito")
            node_id = int(streams[0][0])
            if res.get("restore_token"):
                self._save_token(res["restore_token"])

            reply, fd_list = bus.call_with_unix_fd_list_sync(
                PORTAL_BUS, PORTAL_PATH, SC_IFACE, "OpenPipeWireRemote",
                GLib.Variant("(oa{sv})", (session, {})), GLib.VariantType("(h)"),
                Gio.DBusCallFlags.NONE, -1, None, None,
            )
            fd = fd_list.get(reply.unpack()[0])
            print(f"[wayland_capture] portale OK: node_id={node_id} fd={fd} (portal v{version})", flush=True)
            return fd, node_id
        finally:
            ctx.pop_thread_default()

    @staticmethod
    def _load_token() -> str | None:
        try:
            return TOKEN_FILE.read_text().strip() or None
        except OSError:
            return None

    @staticmethod
    def _save_token(token: str) -> None:
        try:
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_FILE.write_text(token)
            TOKEN_FILE.chmod(0o600)
        except OSError:
            pass

    # --- GStreamer -----------------------------------------------------------
    @staticmethod
    def _node_serial(node_id: int) -> int | None:
        """PipeWire >= 1.x matches target-object on object.serial, not on the id the portal returns."""
        import json
        import shutil
        import subprocess

        exe = shutil.which("pw-dump")
        if not exe:
            return None
        try:
            out = subprocess.run([exe, str(node_id)], capture_output=True, text=True, timeout=5).stdout
            for obj in json.loads(out or "[]"):
                if obj.get("id") == node_id:
                    serial = (obj.get("info") or {}).get("props", {}).get("object.serial")
                    return int(serial) if serial is not None else None
        except Exception:
            pass
        return None

    def _run_pipeline(self, fd: int, node_id: int) -> None:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        Gst.init(None)
        serial = self._node_serial(node_id)
        target = f"target-object={serial}" if serial is not None else f"path={node_id}"
        print(f"[wayland_capture] pipewiresrc {target} (node_id={node_id})", flush=True)
        pipeline = Gst.parse_launch(
            f"pipewiresrc fd={fd} {target} do-timestamp=true keepalive-time=1000 always-copy=true "
            "! videoconvert ! video/x-raw,format=BGRx "
            "! appsink name=sink max-buffers=1 drop=true sync=false emit-signals=false"
        )
        sink = pipeline.get_by_name("sink")
        bus = pipeline.get_bus()
        pipeline.set_state(Gst.State.PLAYING)
        self._pipeline = pipeline
        waited = 0.0
        got_first = False
        try:
            while self._running:
                msg = bus.pop_filtered(Gst.MessageType.ERROR | Gst.MessageType.EOS)
                if msg is not None:
                    if msg.type == Gst.MessageType.ERROR:
                        err, dbg = msg.parse_error()
                        raise PortalError(f"GStreamer: {err.message} ({dbg})")
                    raise PortalError("Stream terminato (condivisione interrotta)")

                sample = sink.emit("try-pull-sample", 500 * Gst.MSECOND)
                if sample is None:
                    waited += 0.5
                    if waited % 5 == 0:
                        print(f"[wayland_capture] nessun frame da {waited:.0f}s...", flush=True)
                    continue
                waited = 0.0
                s = sample.get_caps().get_structure(0)
                if not got_first:
                    got_first = True
                    print(f"[wayland_capture] primo frame, caps: {s.to_string()}", flush=True)
                w, h = s.get_value("width"), s.get_value("height")
                buf = sample.get_buffer()
                ok, info = buf.map(Gst.MapFlags.READ)
                if not ok:
                    continue
                try:
                    data = np.frombuffer(info.data, dtype=np.uint8)
                    stride = data.size // h
                    frame = data[: stride * h].reshape(h, stride)[:, : w * 4].reshape(h, w, 4).copy()
                finally:
                    buf.unmap(info)
                with self._lock:
                    self._frame = frame
                    self._frame_ts = time.monotonic()
        finally:
            pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
            try:
                os.close(fd)
            except OSError:
                pass


def capture_bgra() -> np.ndarray:
    return WaylandScreenCast.get().get_frame()


if __name__ == "__main__":
    import cv2

    print("Avvio sessione ScreenCast... accetta il popup di GNOME.")
    img = capture_bgra()
    print("shape:", img.shape, "max pixel:", int(img.max()))
    time.sleep(1.0)
    img = capture_bgra()
    out = "/tmp/odc_wayland_test.jpg"
    cv2.imwrite(out, cv2.cvtColor(img, cv2.COLOR_BGRA2BGR))
    print("salvato:", out)
    WaylandScreenCast.get().stop()

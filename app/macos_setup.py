from __future__ import annotations

import ctypes
from pathlib import Path
import platform
import sys
import sysconfig


def find_libpython() -> str:
    """Locate the exact libpython dylib path for the active macOS Python interpreter."""
    candidates: list[str] = []

    # 1. Inspect currently loaded dyld images in this Python process
    try:
        libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        libc._dyld_image_count.restype = ctypes.c_uint32
        libc._dyld_get_image_name.argtypes = [ctypes.c_uint32]
        libc._dyld_get_image_name.restype = ctypes.c_char_p
        count = libc._dyld_image_count()
        for idx in range(count):
            raw = libc._dyld_get_image_name(idx)
            if not raw:
                continue
            name = raw.decode("utf-8", errors="ignore")
            if ("libpython" in name or "/Python.framework/" in name) and not name.endswith("/MacOS/Python"):
                candidates.append(name)
    except Exception:
        pass

    # 2. Check sysconfig and base_prefix paths
    ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    base = Path(sys.base_prefix)
    libdir = sysconfig.get_config_var("LIBDIR")
    ldlib = sysconfig.get_config_var("LDLIBRARY")
    if libdir and ldlib:
        candidates.append(str(Path(libdir) / ldlib))
    if libdir:
        candidates.append(str(Path(libdir) / f"libpython{ver}.dylib"))
    candidates.append(str(base / "Python"))
    candidates.append(str(base / "lib" / f"libpython{ver}.dylib"))

    for cand in candidates:
        p = Path(cand)
        if p.is_file():
            try:
                dll = ctypes.CDLL(str(p.resolve()))
                if hasattr(dll, "Py_BytesMain"):
                    return str(p.resolve())
            except Exception:
                continue
    return ""


def write_runtime_config() -> int:
    app_support = Path.home() / "Library" / "Application Support" / "OpenDeskCast"
    app_support.mkdir(parents=True, exist_ok=True)
    cfg_file = app_support / "runtime.cfg"

    libpython = find_libpython()
    if not libpython:
        print("[OpenDeskCast] Errore: impossibile individuare libpython.", file=sys.stderr)
        return 1

    python_home = str(Path(sys.base_prefix).resolve())
    clean_paths = [str(Path(p).resolve()) for p in sys.path[1:] if p and Path(p).exists()]
    python_path = ":".join(clean_paths)
    site_packages = next((p for p in clean_paths if "site-packages" in p), "")
    arch = platform.machine() or "arm64"

    lines = [
        libpython,
        python_home,
        python_path,
        site_packages,
        arch,
    ]
    cfg_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(write_runtime_config())

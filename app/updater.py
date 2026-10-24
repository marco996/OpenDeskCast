from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import time
from typing import Any
import urllib.request

GITHUB_REPO = "marco996/OpenDeskCast"
GITHUB_LATEST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_LATEST_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
CACHE_TTL_SEC = 3600.0  # 1 hour

_cached_update_info: dict[str, Any] | None = None
_cached_update_time: float = 0.0


def parse_version_tuple(v: str) -> tuple[int, ...]:
    clean = (v or "").strip().lstrip("vV")
    main_part = re.split(r"[-+]", clean)[0]
    nums = [int(n) for n in re.findall(r"\d+", main_part)]
    return tuple(nums) if nums else (0,)


def pick_os_asset(assets: list[dict[str, Any]], platform: str = sys.platform) -> str | None:
    if not isinstance(assets, list):
        return None

    if platform.startswith("win"):
        for a in assets:
            name = (a.get("name") or "").lower()
            if name.endswith(".msi") or name.endswith(".exe"):
                return a.get("browser_download_url")
    elif platform.startswith("darwin"):
        for a in assets:
            name = (a.get("name") or "").lower()
            if "macos" in name and name.endswith(".zip"):
                return a.get("browser_download_url")
        for a in assets:
            name = (a.get("name") or "").lower()
            if name.endswith(".dmg") or name.endswith(".zip"):
                return a.get("browser_download_url")
    elif platform.startswith("linux"):
        for a in assets:
            name = (a.get("name") or "").lower()
            if name.endswith(".deb"):
                return a.get("browser_download_url")
        for a in assets:
            name = (a.get("name") or "").lower()
            if name.endswith(".tar.gz"):
                return a.get("browser_download_url")
    return None


def check_for_updates(current_version: str, force: bool = False) -> dict[str, Any]:
    global _cached_update_info, _cached_update_time

    now = time.monotonic()
    if not force and _cached_update_info is not None and (now - _cached_update_time) < CACHE_TTL_SEC:
        return _cached_update_info

    default_result: dict[str, Any] = {
        "checked": True,
        "current_version": current_version,
        "latest_version": None,
        "update_available": False,
        "release_url": GITHUB_LATEST_URL,
        "download_url": GITHUB_LATEST_URL,
        "release_name": "",
    }

    req = urllib.request.Request(
        GITHUB_LATEST_API,
        headers={
            "User-Agent": f"OpenDeskCast/{current_version}",
            "Accept": "application/vnd.github.v3+json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                tag_name = (data.get("tag_name") or "").strip()
                latest_clean = tag_name.lstrip("vV")
                html_url = data.get("html_url") or GITHUB_LATEST_URL
                assets = data.get("assets") or []
                direct_download = pick_os_asset(assets) or html_url
                has_update = parse_version_tuple(latest_clean) > parse_version_tuple(current_version)

                result: dict[str, Any] = {
                    "checked": True,
                    "current_version": current_version,
                    "latest_version": latest_clean or None,
                    "update_available": has_update,
                    "release_url": html_url,
                    "download_url": direct_download,
                    "release_name": data.get("name") or tag_name,
                }
                _cached_update_info = result
                _cached_update_time = now
                return result
    except Exception:
        # Network down, private repo 404, or rate limit: fail silently
        pass

    _cached_update_info = default_result
    _cached_update_time = now
    return default_result

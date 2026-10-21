from __future__ import annotations

from pathlib import Path

from app.server import APP_VERSION
from scripts.verify_clean_env import build_clean_env

ROOT = Path(__file__).resolve().parent.parent


def test_version_and_requirements_present() -> None:
    version_file = ROOT / "VERSION"
    req_file = ROOT / "requirements.txt"
    assert version_file.is_file()
    assert req_file.is_file()
    assert version_file.read_text(encoding="utf-8").strip() == APP_VERSION


def test_launcher_has_no_hardcoded_user_python_and_uses_bundled_engine() -> None:
    src = (ROOT / "launcher.cs").read_text(encoding="utf-8")
    assert "WinUser" not in src
    assert "OpenDeskCastEngine.exe" in src


def test_clean_env_strips_python_variables() -> None:
    env = build_clean_env()
    assert "PYTHONPATH" not in env
    assert "PYTHONHOME" not in env
    assert "VIRTUAL_ENV" not in env
    assert "Python" not in env.get("PATH", "")

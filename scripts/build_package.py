from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"

EXCLUDED_MODULES = [
    "matplotlib",
    "scipy",
    "pandas",
    "pyarrow",
    "vtk",
    "playwright",
    "cadquery",
    "build123d",
    "streamlit",
    "altair",
    "sympy",
    "trimesh",
    "skimage",
    "numba",
    "llvmlite",
    "onnxruntime",
    "rembg",
    "openai",
    "google",
    "lxml",
    "openpyxl",
    "reportlab",
    "pypdf",
    "pdfminer",
    "sqlalchemy",
    "flask",
    "werkzeug",
    "IPython",
    "jedi",
    "pytest",
    "tkinter",
]


def read_version() -> str:
    vfile = ROOT / "VERSION"
    return vfile.read_text(encoding="utf-8").strip() if vfile.is_file() else "1.0.0"


def run_step(cmd: list[str], cwd: Path = ROOT) -> None:
    print(f"[build] Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def build() -> Path:
    version = read_version()
    print(f"=== Building OpenDeskCast v{version} for {sys.platform} ===")

    # 1. Run full test suite first
    run_step([sys.executable, "-m", "pytest", "-v"])

    # 2. Clean previous build artifacts
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    sep = ";" if sys.platform == "win32" else ":"
    exe_name = "OpenDeskCastEngine" if sys.platform == "win32" else "OpenDeskCast"

    pyi_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        exe_name,
        "--add-data",
        f"{ROOT / 'static'}{sep}static",
        "--add-data",
        f"{ROOT / 'VERSION'}{sep}.",
        "--collect-submodules",
        "uvicorn",
        "--collect-submodules",
        "websockets",
    ]

    if (ROOT / "opendeskcast.ico").is_file() and sys.platform == "win32":
        pyi_cmd.extend(["--icon", str(ROOT / "opendeskcast.ico"), "--noconsole"])

    for mod in EXCLUDED_MODULES:
        pyi_cmd.extend(["--exclude-module", mod])

    pyi_cmd.append(str(ROOT / "run.py"))
    run_step(pyi_cmd)

    pkg_root = DIST_DIR / "OpenDeskCast"
    if sys.platform == "win32":
        engine_dist = DIST_DIR / "OpenDeskCastEngine"
        pkg_root.mkdir(parents=True, exist_ok=True)
        target_engine = pkg_root / "engine"
        shutil.move(str(engine_dist), str(target_engine))

        # Compile native Windows Fluent launcher (OpenDeskCast.exe)
        csc = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
        if not csc.is_file():
            raise RuntimeError(f"Compilatore C# non trovato in {csc}")

        out_exe = pkg_root / "OpenDeskCast.exe"
        run_step(
            [
                str(csc),
                "/nologo",
                "/target:winexe",
                f"/out:{out_exe}",
                f"/win32icon:{ROOT / 'opendeskcast.ico'}",
                "/r:System.dll",
                "/r:System.Drawing.dll",
                "/r:System.Windows.Forms.dll",
                str(ROOT / "launcher.cs"),
            ]
        )

        # Also sync standalone executable and engine to workspace root for direct usage
        shutil.copy2(out_exe, ROOT / "OpenDeskCast.exe")
        root_engine = ROOT / "engine"
        if root_engine.exists():
            shutil.rmtree(root_engine)
        shutil.copytree(target_engine, root_engine)

    for doc_file in ("LICENSE", "README.md"):
        src_doc = ROOT / doc_file
        if src_doc.is_file():
            shutil.copy2(src_doc, pkg_root / doc_file)

    if sys.platform == "win32":
        archive_base = DIST_DIR / f"OpenDeskCast-v{version}-windows-x64"
        archive_path = Path(shutil.make_archive(str(archive_base), "zip", root_dir=DIST_DIR, base_dir="OpenDeskCast"))
        try:
            from scripts.build_msi import build_msi
            build_msi()
        except Exception as e:
            print(f"[build] Skip MSI build: {e}")
    elif sys.platform == "darwin":
        archive_base = DIST_DIR / f"OpenDeskCast-v{version}-macos"
        archive_path = Path(shutil.make_archive(str(archive_base), "zip", root_dir=DIST_DIR, base_dir="OpenDeskCast"))
    else:
        archive_base = DIST_DIR / f"OpenDeskCast-v{version}-linux-x64"
        archive_path = Path(shutil.make_archive(str(archive_base), "gztar", root_dir=DIST_DIR, base_dir="OpenDeskCast"))

    print(f"[build] Standalone package ready: {archive_path} ({archive_path.stat().st_size // 1024} KB)")
    return archive_path


if __name__ == "__main__":
    build()

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
SOURCE_DIR = DIST_DIR / "OpenDeskCast"
BUILD_DIR = ROOT / "build" / "msi"


def sanitize_id(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.]", "_", text)
    if cleaned and cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned[:64]


def read_version() -> str:
    vfile = ROOT / "VERSION"
    return vfile.read_text(encoding="utf-8").strip() if vfile.is_file() else "1.0.0"


def find_wix() -> Path:
    candidates = [
        Path(os.environ.get("USERPROFILE", "")) / ".dotnet" / "tools" / "wix.exe",
        Path(shutil.which("wix") or ""),
    ]
    for c in candidates:
        if c and c.is_file():
            return c
    raise RuntimeError("WiX v4 non trovato. Installa con: dotnet tool install --global wix --version 4.0.5")


def generate_wxs(version: str, wxs_path: Path) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        '<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">',
        '  <Package Name="OpenDeskCast"',
        '           Manufacturer="OpenDeskCast Contributors"',
        f'           Version="{version}"',
        '           UpgradeCode="D8F9A102-3B47-4C79-8812-7F3A591240EE"',
        '           Scope="perUser">',
        '    <MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." />',
        '    <MediaTemplate EmbedCab="yes" CompressionLevel="high" />',
        '    <Icon Id="AppIcon" SourceFile="opendeskcast.ico" />',
        '    <Property Id="ARPPRODUCTICON" Value="AppIcon" />',
        '    <StandardDirectory Id="LocalAppDataFolder">',
        '      <Directory Id="ProgramsFolder" Name="Programs">',
        '        <Directory Id="INSTALLFOLDER" Name="OpenDeskCast">',
    ]

    component_ids: list[str] = []

    # Map directories and files
    rel_dirs: dict[str, str] = {"": "INSTALLFOLDER"}
    dir_counter = 0
    comp_counter = 0

    for root, dirs, files in os.walk(SOURCE_DIR):
        rel_root = os.path.relpath(root, SOURCE_DIR)
        current_dir_rel = "" if rel_root == "." else rel_root.replace("\\", "/")

        if current_dir_rel != "":
            parent_rel = "/".join(current_dir_rel.split("/")[:-1])
            parent_id = rel_dirs[parent_rel]
            dir_name = os.path.basename(root)
            dir_counter += 1
            dir_id = f"Dir_{dir_counter}_{sanitize_id(dir_name)}"
            rel_dirs[current_dir_rel] = dir_id

    # Construct nested directories structure
    file_counter = 0

    def write_dir(rel_path: str, indent: str) -> None:
        nonlocal comp_counter, file_counter
        curr_id = rel_dirs[rel_path]
        curr_fs_path = SOURCE_DIR if not rel_path else SOURCE_DIR / rel_path

        # Find immediate subdirs
        subdirs = [
            d for d in os.listdir(curr_fs_path) if (curr_fs_path / d).is_dir()
        ]
        files = [
            f for f in os.listdir(curr_fs_path) if (curr_fs_path / f).is_file()
        ]

        for f in files:
            file_counter += 1
            cid = f"C_{file_counter}_{sanitize_id(f)}"
            fid = f"F_{file_counter}_{sanitize_id(f)}"
            component_ids.append(cid)
            fpath = curr_fs_path / f
            src = str(fpath.resolve())
            lines.append(f'{indent}<Component Id="{cid}" Directory="{curr_id}">')
            if f == "OpenDeskCast.exe" and rel_path == "":
                lines.append(f'{indent}  <File Id="{fid}" Source="{src}" KeyPath="yes">')
                lines.append('    <Shortcut Id="DesktopShortcut" Directory="DesktopFolder" Name="OpenDeskCast"')
                lines.append('              WorkingDirectory="INSTALLFOLDER" Icon="AppIcon" Advertise="yes" />')
                lines.append('    <Shortcut Id="StartMenuShortcut" Directory="ProgramMenuFolder" Name="OpenDeskCast"')
                lines.append('              WorkingDirectory="INSTALLFOLDER" Icon="AppIcon" Advertise="yes" />')
                lines.append(f'{indent}  </File>')
            else:
                lines.append(f'{indent}  <File Id="{fid}" Source="{src}" KeyPath="yes" />')
            lines.append(f'{indent}</Component>')

        for d in sorted(subdirs):
            child_rel = d if not rel_path else f"{rel_path}/{d}"
            child_id = rel_dirs[child_rel]
            lines.append(f'{indent}<Directory Id="{child_id}" Name="{d}">')
            write_dir(child_rel, indent + "  ")
            lines.append(f'{indent}</Directory>')

    write_dir("", "          ")

    lines.extend([
        '        </Directory>',
        '      </Directory>',
        '    </StandardDirectory>',
        '    <StandardDirectory Id="ProgramMenuFolder" />',
        '    <StandardDirectory Id="DesktopFolder" />',
        '    <Feature Id="MainFeature" Title="OpenDeskCast" Level="1">',
    ])

    for cid in component_ids:
        lines.append(f'      <ComponentRef Id="{cid}" />')

    lines.extend([
        '    </Feature>',
        '  </Package>',
        '</Wix>',
    ])

    wxs_path.write_text("\n".join(lines), encoding="utf-8")


def build_msi() -> Path:
    wix = find_wix()
    version = read_version()
    wxs_file = BUILD_DIR / "OpenDeskCast.wxs"
    msi_output = DIST_DIR / f"OpenDeskCast-v{version}-windows-x64.msi"

    if not SOURCE_DIR.is_dir():
        raise RuntimeError(f"Cartella sorgente {SOURCE_DIR} non trovata. Esegui prima scripts/build_package.py.")

    print(f"[msi] Generazione WXS in {wxs_file}...")
    generate_wxs(version, wxs_file)

    cmd = [
        str(wix),
        "build",
        "-arch",
        "x64",
        str(wxs_file),
        "-out",
        str(msi_output),
    ]
    print(f"[msi] Compilazione MSI con: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    print(f"[msi] Pacchetto MSI creato con successo: {msi_output} ({msi_output.stat().st_size // 1024} KB)")
    return msi_output


if __name__ == "__main__":
    build_msi()

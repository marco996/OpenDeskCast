from __future__ import annotations

import io
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
SOURCE_DIR = DIST_DIR / "OpenDeskCast-linux" if (DIST_DIR / "OpenDeskCast-linux").exists() else DIST_DIR / "OpenDeskCast"
BUILD_DIR = ROOT / "build" / "deb"


def read_version() -> str:
    vfile = ROOT / "VERSION"
    return vfile.read_text(encoding="utf-8").strip() if vfile.is_file() else "1.0.0"


def calculate_installed_size_kb(directory: Path) -> int:
    total = 0
    for root, _, files in os.walk(directory):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
            except Exception:
                pass
    return max(1, total // 1024)


def create_ar_archive(out_path: Path, members: list[tuple[str, bytes]]) -> None:
    """Pack members into a standard Unix 'ar' archive (Debian .deb package format)."""
    with open(out_path, "wb") as f:
        f.write(b"!<arch>\n")
        for name, data in members:
            # ar header is 60 bytes:
            # name (16), mtime (12), uid (6), gid (6), mode (8), size (10), magic (2)
            name_padded = name.ljust(16).encode("ascii")
            mtime = str(int(time.time())).ljust(12).encode("ascii")
            uid = b"0".ljust(6)
            gid = b"0".ljust(6)
            mode = b"100644".ljust(8)
            size = str(len(data)).ljust(10).encode("ascii")
            magic = b"\x60\x0a"
            header = name_padded + mtime + uid + gid + mode + size + magic
            f.write(header)
            f.write(data)
            if len(data) % 2 != 0:
                f.write(b"\n")


def build_deb_pure_python(pkg_root: Path, out_deb: Path) -> None:
    """Build .deb using standard library tarfile and ar packager."""
    # 1. debian-binary
    deb_binary = b"2.0\n"

    # 2. control.tar.gz
    control_buf = io.BytesIO()
    with tarfile.open(fileobj=control_buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        for item in (pkg_root / "DEBIAN").iterdir():
            ti = tar.gettarinfo(str(item), arcname=f"./{item.name}")
            ti.uid = 0
            ti.gid = 0
            ti.uname = "root"
            ti.gname = "root"
            if item.name in {"postinst", "postrm", "preinst", "prerm"}:
                ti.mode = 0o755
            else:
                ti.mode = 0o644
            if item.is_file():
                with open(item, "rb") as f:
                    tar.addfile(ti, f)
            else:
                tar.addfile(ti)
    control_data = control_buf.getvalue()

    # 3. data.tar.gz
    data_buf = io.BytesIO()
    with tarfile.open(fileobj=data_buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        for top_dir in ("opt", "usr"):
            src_dir = pkg_root / top_dir
            if not src_dir.exists():
                continue
            for root, dirs, files in os.walk(src_dir):
                rel_root = os.path.relpath(root, pkg_root).replace("\\", "/")
                dir_info = tar.gettarinfo(root, arcname=f"./{rel_root}")
                dir_info.uid = 0
                dir_info.gid = 0
                dir_info.uname = "root"
                dir_info.gname = "root"
                dir_info.mode = 0o755
                tar.addfile(dir_info)

                for f in files:
                    fp = Path(root) / f
                    rel_file = os.path.relpath(fp, pkg_root).replace("\\", "/")
                    file_info = tar.gettarinfo(str(fp), arcname=f"./{rel_file}")
                    file_info.uid = 0
                    file_info.gid = 0
                    file_info.uname = "root"
                    file_info.gname = "root"
                    if "bin" in rel_file or fp.name == "OpenDeskCast":
                        file_info.mode = 0o755
                    else:
                        file_info.mode = 0o644
                    with open(fp, "rb") as ff:
                        tar.addfile(file_info, ff)

    data_data = data_buf.getvalue()

    create_ar_archive(
        out_deb,
        [
            ("debian-binary", deb_binary),
            ("control.tar.gz", control_data),
            ("data.tar.gz", data_data),
        ],
    )


def build_deb_from_tar(tar_path: Path, out_deb: Path, version: str) -> None:
    """Build .deb directly from a Linux tar.gz release archive, updating static files."""
    deb_binary = b"2.0\n"

    # control.tar.gz
    control_buf = io.BytesIO()
    with tarfile.open(fileobj=control_buf, mode="w:gz", format=tarfile.GNU_FORMAT) as ctar:
        control_content = f"""Package: opendeskcast
Version: {version}
Architecture: amd64
Maintainer: Marco Scaglione <marcoscaglione96@gmail.com>
Installed-Size: 105000
Depends: pulseaudio-utils | pipewire-bin, libgl1
Recommends: python3-gi, gir1.2-gst-plugins-base-1.0, gstreamer1.0-pipewire
Section: net
Priority: optional
Homepage: https://github.com/marco996/OpenDeskCast
Description: Trasmissione schermo e audio PC a qualsiasi browser locale
 OpenDeskCast consente la trasmissione istantanea e fluida dello schermo
 e dell'audio di sistema verso qualsiasi smartphone, tablet o browser nella
 stessa rete locale senza installare alcuna app sul dispositivo ricevente.
""".encode("utf-8")
        ti = tarfile.TarInfo("./control")
        ti.size = len(control_content)
        ti.mode = 0o644
        ti.mtime = int(time.time())
        ti.uid = 0
        ti.gid = 0
        ti.uname = "root"
        ti.gname = "root"
        ctar.addfile(ti, io.BytesIO(control_content))

        postinst_content = b"""#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
"""
        ti = tarfile.TarInfo("./postinst")
        ti.size = len(postinst_content)
        ti.mode = 0o755
        ti.mtime = int(time.time())
        ti.uid = 0
        ti.gid = 0
        ti.uname = "root"
        ti.gname = "root"
        ctar.addfile(ti, io.BytesIO(postinst_content))

        postrm_content = b"""#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
    fi
fi
exit 0
"""
        ti = tarfile.TarInfo("./postrm")
        ti.size = len(postrm_content)
        ti.mode = 0o755
        ti.mtime = int(time.time())
        ti.uid = 0
        ti.gid = 0
        ti.uname = "root"
        ti.gname = "root"
        ctar.addfile(ti, io.BytesIO(postrm_content))

    control_data = control_buf.getvalue()

    # data.tar.gz
    data_buf = io.BytesIO()
    static_dir = ROOT / "static"
    with tarfile.open(fileobj=data_buf, mode="w:gz", format=tarfile.GNU_FORMAT) as dtar:
        for dpath in (
            "./opt",
            "./opt/opendeskcast",
            "./opt/opendeskcast/app",
            "./usr",
            "./usr/bin",
            "./usr/share",
            "./usr/share/applications",
            "./usr/share/icons",
            "./usr/share/icons/hicolor",
            "./usr/share/icons/hicolor/256x256",
            "./usr/share/icons/hicolor/256x256/apps",
        ):
            dinfo = tarfile.TarInfo(dpath)
            dinfo.type = tarfile.DIRTYPE
            dinfo.mode = 0o755
            dinfo.mtime = int(time.time())
            dinfo.uid = 0
            dinfo.gid = 0
            dinfo.uname = "root"
            dinfo.gname = "root"
            dtar.addfile(dinfo)

        launcher = (
            b"#!/bin/sh\n"
            b"if [ -f \"/opt/opendeskcast/run.py\" ] && [ -x \"/opt/opendeskcast/.venv/bin/python3\" ]; then\n"
            b"    exec /opt/opendeskcast/.venv/bin/python3 /opt/opendeskcast/run.py \"$@\"\n"
            b"elif [ -f \"/opt/opendeskcast/run.py\" ] && command -v python3 >/dev/null 2>&1 && python3 -c \"import fastapi, uvicorn, mss, cv2\" >/dev/null 2>&1; then\n"
            b"    exec python3 /opt/opendeskcast/run.py \"$@\"\n"
            b"elif [ \"${XDG_SESSION_TYPE:-}\" = \"wayland\" ] || [ -n \"${WAYLAND_DISPLAY:-}\" ]; then\n"
            b"    if [ -x \"/opt/opendeskcast/run_linux.sh\" ] && command -v python3 >/dev/null 2>&1; then\n"
            b"        exec /opt/opendeskcast/run_linux.sh \"$@\"\n"
            b"    fi\n"
            b"fi\n"
            b"exec /opt/opendeskcast/OpenDeskCast \"$@\"\n"
        )
        linfo = tarfile.TarInfo("./usr/bin/opendeskcast")
        linfo.size = len(launcher)
        linfo.mode = 0o755
        linfo.mtime = int(time.time())
        linfo.uid = 0
        linfo.gid = 0
        linfo.uname = "root"
        linfo.gname = "root"
        dtar.addfile(linfo, io.BytesIO(launcher))

        for extra_rel, extra_mode in (
            ("run.py", 0o755),
            ("run_linux.sh", 0o755),
            ("requirements.txt", 0o644),
            ("app/__init__.py", 0o644),
            ("app/server.py", 0o644),
            ("app/capture.py", 0o644),
            ("app/wayland_capture.py", 0o644),
            ("app/audio.py", 0o644),
        ):
            src_f = ROOT / extra_rel
            if src_f.is_file():
                f_bytes = src_f.read_bytes().replace(b"\r\n", b"\n") if extra_rel.endswith(".sh") else src_f.read_bytes()
                eti = tarfile.TarInfo(f"./opt/opendeskcast/{extra_rel}")
                eti.size = len(f_bytes)
                eti.mode = extra_mode
                eti.mtime = int(time.time())
                eti.uid = 0
                eti.gid = 0
                eti.uname = "root"
                eti.gname = "root"
                dtar.addfile(eti, io.BytesIO(f_bytes))

        desktop_bytes = """[Desktop Entry]
Version=1.0
Type=Application
Name=OpenDeskCast
GenericName=Desktop Screen Casting
Comment=Trasmetti lo schermo del PC a qualsiasi smartphone, tablet o browser locale
Exec=/usr/bin/opendeskcast
Icon=opendeskcast
Terminal=false
Categories=Network;AudioVideo;Utility;
StartupWMClass=opendeskcast
Keywords=cast;screen;stream;mirror;desktop;
""".encode("utf-8")
        dentry = tarfile.TarInfo("./usr/share/applications/opendeskcast.desktop")
        dentry.size = len(desktop_bytes)
        dentry.mode = 0o644
        dentry.mtime = int(time.time())
        dentry.uid = 0
        dentry.gid = 0
        dentry.uname = "root"
        dentry.gname = "root"
        dtar.addfile(dentry, io.BytesIO(desktop_bytes))

        icon_p = static_dir / "icon.png"
        if icon_p.exists():
            icon_bytes = icon_p.read_bytes()
            icinfo = tarfile.TarInfo("./usr/share/icons/hicolor/256x256/apps/opendeskcast.png")
            icinfo.size = len(icon_bytes)
            icinfo.mode = 0o644
            icinfo.mtime = int(time.time())
            icinfo.uid = 0
            icinfo.gid = 0
            icinfo.uname = "root"
            icinfo.gname = "root"
            dtar.addfile(icinfo, io.BytesIO(icon_bytes))

        with tarfile.open(tar_path, "r:gz") as src_tar:
            for m in src_tar.getmembers():
                parts = m.name.split("/", 1)
                rel_name = parts[1] if len(parts) > 1 else ""
                if not rel_name:
                    continue
                target_arcname = f"./opt/opendeskcast/{rel_name}"

                is_updated_static = False
                if rel_name == "VERSION" or rel_name.endswith("/VERSION"):
                    v_bytes = f"{version}\n".encode("utf-8")
                    new_ti = tarfile.TarInfo(target_arcname)
                    new_ti.size = len(v_bytes)
                    new_ti.mode = 0o644
                    new_ti.mtime = int(time.time())
                    new_ti.uid = 0
                    new_ti.gid = 0
                    new_ti.uname = "root"
                    new_ti.gname = "root"
                    dtar.addfile(new_ti, io.BytesIO(v_bytes))
                    continue

                for sname in ("client.js", "index.html", "style.css", "admin.html", "admin.js"):
                    if rel_name.endswith(f"static/{sname}"):
                        local_f = static_dir / sname
                        if local_f.exists():
                            updated_bytes = local_f.read_bytes()
                            new_ti = tarfile.TarInfo(target_arcname)
                            new_ti.size = len(updated_bytes)
                            new_ti.mode = 0o644
                            new_ti.mtime = int(time.time())
                            new_ti.uid = 0
                            new_ti.gid = 0
                            new_ti.uname = "root"
                            new_ti.gname = "root"
                            dtar.addfile(new_ti, io.BytesIO(updated_bytes))
                            is_updated_static = True
                            break
                if is_updated_static:
                    continue

                m.name = target_arcname
                m.uid = 0
                m.gid = 0
                m.uname = "root"
                m.gname = "root"
                if m.isreg():
                    f_obj = src_tar.extractfile(m)
                    dtar.addfile(m, f_obj)
                else:
                    dtar.addfile(m)

    data_data = data_buf.getvalue()

    create_ar_archive(
        out_deb,
        [
            ("debian-binary", deb_binary),
            ("control.tar.gz", control_data),
            ("data.tar.gz", data_data),
        ],
    )


def build_deb() -> Path:
    version = read_version()
    deb_filename = f"opendeskcast_{version}_amd64.deb"
    out_deb = DIST_DIR / deb_filename
    linux_tar = DIST_DIR / f"OpenDeskCast-v{version}-linux-x64.tar.gz"
    if not linux_tar.is_file():
        candidates = sorted(DIST_DIR.glob("OpenDeskCast-v*-linux-x64.tar.gz"))
        if candidates:
            linux_tar = candidates[-1]

    print(f"=== [DEB] Creazione pacchetto nativo Debian/Ubuntu {deb_filename} ===")

    if sys.platform == "win32" and linux_tar.is_file():
        print(f"[deb] Windows host: creazione diretta da archivio Linux {linux_tar.name}...")
        build_deb_from_tar(linux_tar, out_deb, version)
        print(f"[deb] Pacchetto Debian/Ubuntu creato con successo: {out_deb} ({out_deb.stat().st_size // 1024} KB)")
        return out_deb

    if not SOURCE_DIR.is_dir():
        raise RuntimeError(f"Cartella sorgente {SOURCE_DIR} non trovata. Esegui prima scripts/build_package.py.")

    if sys.platform != "win32":
        deb_build_dir = Path("/tmp/opendeskcast_deb_build")
    else:
        deb_build_dir = BUILD_DIR
    if deb_build_dir.exists():
        shutil.rmtree(deb_build_dir)

    pkg_root = deb_build_dir / "package"
    debian_dir = pkg_root / "DEBIAN"
    opt_dir = pkg_root / "opt" / "opendeskcast"
    bin_dir = pkg_root / "usr" / "bin"
    apps_dir = pkg_root / "usr" / "share" / "applications"
    icons_dir = pkg_root / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"

    for d in (debian_dir, opt_dir, bin_dir, apps_dir, icons_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1. Copia file applicazione in /opt/opendeskcast
    print(f"[deb] Copia file applicazione in {opt_dir}...")
    shutil.copytree(SOURCE_DIR, opt_dir, dirs_exist_ok=True)

    # Assicura permessi di esecuzione per il binario OpenDeskCast
    bin_target = opt_dir / "OpenDeskCast"
    if bin_target.is_file():
        try:
            bin_target.chmod(bin_target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except Exception:
            pass

    # 2. Crea script wrapper /usr/bin/opendeskcast
    launcher_script = bin_dir / "opendeskcast"
    launcher_script.write_text(
        "#!/bin/sh\nexec /opt/opendeskcast/OpenDeskCast \"$@\"\n",
        encoding="utf-8",
    )
    try:
        launcher_script.chmod(0o755)
    except Exception:
        pass

    # 3. Crea icona e file .desktop per il menù applicazioni di sistema
    icon_source = ROOT / "static" / "icon.png"
    if icon_source.is_file():
        shutil.copy2(icon_source, icons_dir / "opendeskcast.png")

    desktop_file = apps_dir / "opendeskcast.desktop"
    desktop_content = """[Desktop Entry]
Version=1.0
Type=Application
Name=OpenDeskCast
GenericName=Desktop Screen Casting
Comment=Trasmetti lo schermo del PC a qualsiasi smartphone, tablet o browser locale
Exec=/usr/bin/opendeskcast
Icon=opendeskcast
Terminal=false
Categories=Network;AudioVideo;Utility;
StartupWMClass=opendeskcast
Keywords=cast;screen;stream;mirror;desktop;
"""
    desktop_file.write_text(desktop_content, encoding="utf-8")

    # 4. Calcola Installed-Size
    installed_size_kb = calculate_installed_size_kb(opt_dir) + 16

    # 5. Genera file DEBIAN/control
    control_file = debian_dir / "control"
    control_content = f"""Package: opendeskcast
Version: {version}
Architecture: amd64
Maintainer: Marco Scaglione <marcoscaglione96@gmail.com>
Installed-Size: {installed_size_kb}
Depends: pulseaudio-utils, libgl1
Section: net
Priority: optional
Homepage: https://github.com/marco996/OpenDeskCast
Description: Trasmissione schermo e audio PC a qualsiasi browser locale
 OpenDeskCast consente la trasmissione istantanea e fluida dello schermo
 e dell'audio di sistema verso qualsiasi smartphone, tablet o browser nella
 stessa rete locale senza installare alcuna app sul dispositivo ricevente.
"""
    control_file.write_text(control_content, encoding="utf-8")

    # 6. Genera script DEBIAN/postinst e DEBIAN/postrm per aggiornare le cache delle icone
    postinst_file = debian_dir / "postinst"
    postinst_file.write_text(
        "#!/bin/sh\nset -e\n"
        "if command -v update-desktop-database >/dev/null 2>&1; then\n"
        "    update-desktop-database -q /usr/share/applications || true\n"
        "fi\n"
        "if command -v gtk-update-icon-cache >/dev/null 2>&1; then\n"
        "    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    try:
        postinst_file.chmod(0o755)
    except Exception:
        pass

    postrm_file = debian_dir / "postrm"
    postrm_file.write_text(
        "#!/bin/sh\nset -e\n"
        "if [ \"$1\" = \"remove\" ] || [ \"$1\" = \"purge\" ]; then\n"
        "    if command -v update-desktop-database >/dev/null 2>&1; then\n"
        "        update-desktop-database -q /usr/share/applications || true\n"
        "    fi\n"
        "    if command -v gtk-update-icon-cache >/dev/null 2>&1; then\n"
        "        gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true\n"
        "    fi\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    try:
        postrm_file.chmod(0o755)
    except Exception:
        pass

    # 7. Compilazione pacchetto .deb
    dpkg_deb = shutil.which("dpkg-deb")
    if dpkg_deb and sys.platform != "win32":
        print(f"[deb] Compilazione con dpkg-deb: {dpkg_deb}...")
        subprocess.run(
            [dpkg_deb, "--build", "--root-owner-group", str(pkg_root), str(out_deb)],
            check=True,
        )
    else:
        print("[deb] Compilazione con builder Python nativo...")
        build_deb_pure_python(pkg_root, out_deb)

    print(f"[deb] Pacchetto Debian/Ubuntu creato con successo: {out_deb} ({out_deb.stat().st_size // 1024} KB)")
    return out_deb


if __name__ == "__main__":
    build_deb()

from __future__ import annotations

from pathlib import Path
import stat
import time
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build" / "macos_app"


def read_version() -> str:
    vfile = ROOT / "VERSION"
    return vfile.read_text(encoding="utf-8").strip() if vfile.is_file() else "1.0.0"


MACOS_LAUNCHER_C = r"""// OpenDeskCast — Native macOS Mach-O Bundle Executable
// Runs Python in-process via dlopen(libpython) so macOS TCC attributes
// Screen Recording (kTCCServiceScreenCapture) directly to OpenDeskCast.app.

#include <ApplicationServices/ApplicationServices.h>
#include <CoreFoundation/CoreFoundation.h>
#include <CoreGraphics/CoreGraphics.h>
#include <dlfcn.h>
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

typedef int (*Py_BytesMain_Func)(int argc, char **argv);

static void trim_newline(char *s) {
    if (!s) return;
    size_t len = strlen(s);
    while (len > 0 && (s[len - 1] == '\n' || s[len - 1] == '\r')) {
        s[--len] = '\0';
    }
}

static int path_exists(const char *path) {
    struct stat st;
    return (path && path[0] != '\0' && stat(path, &st) == 0);
}

int main(int argc, char *argv[]) {
    char exe_path[PATH_MAX];
    uint32_t size = sizeof(exe_path);
    if (_NSGetExecutablePath(exe_path, &size) != 0) {
        fprintf(stderr, "[OpenDeskCast] Impossibile determinare il percorso eseguibile.\n");
        return 1;
    }

    char real_exe[PATH_MAX];
    if (!realpath(exe_path, real_exe)) {
        strncpy(real_exe, exe_path, sizeof(real_exe) - 1);
        real_exe[sizeof(real_exe) - 1] = '\0';
    }

    char macos_dir[PATH_MAX];
    strncpy(macos_dir, real_exe, sizeof(macos_dir) - 1);
    macos_dir[sizeof(macos_dir) - 1] = '\0';
    char *dir_ptr = dirname(macos_dir);

    char resources_dir[PATH_MAX];
    snprintf(resources_dir, sizeof(resources_dir), "%s/../Resources", dir_ptr);

    char real_resources[PATH_MAX];
    if (!realpath(resources_dir, real_resources)) {
        strncpy(real_resources, resources_dir, sizeof(real_resources) - 1);
        real_resources[sizeof(real_resources) - 1] = '\0';
    }

    const char *home = getenv("HOME");
    if (!home) home = "/tmp";

    char cfg_path[PATH_MAX];
    snprintf(cfg_path, sizeof(cfg_path),
             "%s/Library/Application Support/OpenDeskCast/runtime.cfg", home);

    char bootstrap_sh[PATH_MAX];
    snprintf(bootstrap_sh, sizeof(bootstrap_sh), "%s/bootstrap_macos.sh", real_resources);

    char libpython[PATH_MAX] = {0};
    char python_home[PATH_MAX] = {0};
    char python_path[PATH_MAX * 4] = {0};
    char site_packages[PATH_MAX] = {0};

    FILE *fp = fopen(cfg_path, "r");
    if (fp) {
        if (fgets(libpython, sizeof(libpython), fp)) trim_newline(libpython);
        if (fgets(python_home, sizeof(python_home), fp)) trim_newline(python_home);
        if (fgets(python_path, sizeof(python_path), fp)) trim_newline(python_path);
        if (fgets(site_packages, sizeof(site_packages), fp)) trim_newline(site_packages);
        fclose(fp);
    }

    if (!path_exists(libpython) || !path_exists(python_home) || !path_exists(site_packages)) {
        char cmd[PATH_MAX * 2];
        snprintf(cmd, sizeof(cmd), "/bin/bash \"%s\" --setup-only", bootstrap_sh);
        int rc = system(cmd);
        if (rc != 0) {
            return rc;
        }
        fp = fopen(cfg_path, "r");
        if (!fp) {
            fprintf(stderr, "[OpenDeskCast] runtime.cfg non trovato dopo il setup.\n");
            return 1;
        }
        if (fgets(libpython, sizeof(libpython), fp)) trim_newline(libpython);
        if (fgets(python_home, sizeof(python_home), fp)) trim_newline(python_home);
        if (fgets(python_path, sizeof(python_path), fp)) trim_newline(python_path);
        if (fgets(site_packages, sizeof(site_packages), fp)) trim_newline(site_packages);
        fclose(fp);
    }

    // Request macOS Screen Recording permission directly from this native Mach-O binary
    if (!CGPreflightScreenCaptureAccess()) {
        CGRequestScreenCaptureAccess();
    }

    char full_pythonpath[PATH_MAX * 5];
    snprintf(full_pythonpath, sizeof(full_pythonpath), "%s:%s", real_resources, python_path);

    setenv("PYTHONHOME", python_home, 1);
    setenv("PYTHONPATH", full_pythonpath, 1);
    setenv("OPENDESKCAST_SITE_PACKAGES", site_packages, 1);
    setenv("PYTHONUTF8", "1", 1);
    unsetenv("__PYVENV_LAUNCHER__");

    if (chdir(real_resources) != 0) {
        perror("[OpenDeskCast] chdir Resources fallito");
    }

    void *handle = dlopen(libpython, RTLD_LAZY | RTLD_GLOBAL);
    if (!handle) {
        fprintf(stderr, "[OpenDeskCast] dlopen(%s) fallito: %s\n", libpython, dlerror());
        char fallback_cmd[PATH_MAX * 2];
        snprintf(fallback_cmd, sizeof(fallback_cmd), "/bin/bash \"%s\" --run-fallback", bootstrap_sh);
        return system(fallback_cmd);
    }

    Py_BytesMain_Func py_main = (Py_BytesMain_Func)dlsym(handle, "Py_BytesMain");
    if (!py_main) {
        fprintf(stderr, "[OpenDeskCast] Simbolo Py_BytesMain non trovato: %s\n", dlerror());
        return 1;
    }

    char run_py[PATH_MAX];
    snprintf(run_py, sizeof(run_py), "%s/run.py", real_resources);

    char **py_argv = (char **)calloc((size_t)argc + 2, sizeof(char *));
    int py_argc = 0;
    py_argv[py_argc++] = argv[0];
    py_argv[py_argc++] = run_py;
    for (int i = 1; i < argc; i++) {
        if (strncmp(argv[i], "-psn_", 5) == 0) {
            continue;
        }
        py_argv[py_argc++] = argv[i];
    }
    py_argv[py_argc] = NULL;

    return py_main(py_argc, py_argv);
}
"""


BOOTSTRAP_MACOS_SH = r"""#!/usr/bin/env bash
# OpenDeskCast — macOS Self-Guided Bootstrap & Native Mach-O Wrapper Builder
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
MACOS_DIR="$(cd "$APP_DIR/../MacOS" && pwd)"
BUNDLE_DIR="$(cd "$APP_DIR/../.." && pwd)"
APP_VERSION="$(cat "$APP_DIR/VERSION" 2>/dev/null | tr -d '\r\n' || echo "1.0.8")"
cd "$APP_DIR"

MODE="${1:-}"

# 0. Rimuovi automaticamente eventuale attributo di quarantena Gatekeeper sul bundle
/usr/bin/xattr -cr "$BUNDLE_DIR" >/dev/null 2>&1 || true

# 1. Trova Python 3 su macOS (Homebrew, Framework o Command Line Tools)
PYTHON_BIN=""
for candidate in \
    "/opt/homebrew/bin/python3" \
    "/usr/local/bin/python3" \
    "/Library/Frameworks/Python.framework/Versions/Current/bin/python3" \
    "/usr/bin/python3" \
    "$(command -v python3 2>/dev/null)" \
    "$(command -v python 2>/dev/null)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        if [ "$candidate" = "/usr/bin/python3" ] && ! /usr/bin/xcode-select -p >/dev/null 2>&1; then
            continue
        fi
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    CHOICE="$(osascript -e 'button returned of (display dialog "OpenDeskCast richiede gli strumenti Python di sistema per funzionare su macOS.\n\nVuoi avviarne l'\''installazione guidata adesso?" buttons {"Annulla", "Installa Ora"} default button "Installa Ora" with title "Installazione Guidata OpenDeskCast")' 2>/dev/null || echo "Annulla")"
    if [ "$CHOICE" = "Installa Ora" ]; then
        /usr/bin/xcode-select --install >/dev/null 2>&1 || open "https://www.python.org/downloads/macos/"
    fi
    exit 1
fi

# 2. Configura ambiente virtuale isolato per OpenDeskCast in Library/Application Support
SUPPORT_DIR="$HOME/Library/Application Support/OpenDeskCast"
VENV_DIR="$SUPPORT_DIR/venv"
INIT_MARKER="$SUPPORT_DIR/bundle_init_v${APP_VERSION}"
mkdir -p "$SUPPORT_DIR"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    osascript -e 'display notification "Configurazione automatica del primo avvio in corso (circa 15 secondi)..." with title "OpenDeskCast" subtitle "Attendere l'\''apertura automatica della regia"' >/dev/null 2>&1 || true
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip --quiet
    "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" --quiet
fi

# 3. Genera runtime.cfg con il percorso esatto di libpython e dell'eseguibile Mach-O
"$VENV_DIR/bin/python" "$APP_DIR/app/macos_setup.py"

PY_LIB="$(sed -n '1p' "$SUPPORT_DIR/runtime.cfg" 2>/dev/null || true)"
PY_HOME="$(sed -n '2p' "$SUPPORT_DIR/runtime.cfg" 2>/dev/null || true)"
PY_PATH="$(sed -n '3p' "$SUPPORT_DIR/runtime.cfg" 2>/dev/null || true)"
PY_SITE="$(sed -n '4p' "$SUPPORT_DIR/runtime.cfg" 2>/dev/null || true)"
PY_ARCH="$(sed -n '5p' "$SUPPORT_DIR/runtime.cfg" 2>/dev/null || uname -m)"
PY_MACHO="$(sed -n '6p' "$SUPPORT_DIR/runtime.cfg" 2>/dev/null || true)"

# 4. Prepara il binario nativo Mach-O dentro Contents/MacOS e firma OpenDeskCast.app
if [ -w "$MACOS_DIR" ]; then
    BUILT_NATIVE=0
    if /usr/bin/xcode-select -p >/dev/null 2>&1 && [ -x "/usr/bin/cc" ]; then
        if /usr/bin/cc -O2 -arch "$PY_ARCH" \
            -framework CoreGraphics -framework CoreFoundation -framework ApplicationServices \
            "$APP_DIR/macos_launcher.c" -o "$MACOS_DIR/OpenDeskCast.bin" 2>/dev/null; then
            mv -f "$MACOS_DIR/OpenDeskCast.bin" "$MACOS_DIR/OpenDeskCast"
            chmod 755 "$MACOS_DIR/OpenDeskCast"
            BUILT_NATIVE=1
        fi
    fi

    if [ "$BUILT_NATIVE" = "0" ] && [ -n "$PY_MACHO" ] && [ -f "$PY_MACHO" ]; then
        cp -f "$PY_MACHO" "$MACOS_DIR/OpenDeskCastBin"
        chmod 755 "$MACOS_DIR/OpenDeskCastBin"
    fi

    if [ ! -f "$INIT_MARKER" ]; then
        /usr/bin/codesign --force --deep --sign - "$BUNDLE_DIR" >/dev/null 2>&1 || true
        /usr/bin/tccutil reset ScreenCapture com.opendeskcast.app >/dev/null 2>&1 || true
        echo "$APP_VERSION" > "$INIT_MARKER"
    fi
fi

if [ "$MODE" = "--setup-only" ]; then
    exit 0
fi

if [ "$MODE" = "--run-fallback" ]; then
    shift
    export PYTHONHOME="$PY_HOME"
    export PYTHONPATH="$APP_DIR:$PY_PATH"
    export OPENDESKCAST_SITE_PACKAGES="$PY_SITE"
    export PYTHONUTF8="1"
    unset __PYVENV_LAUNCHER__
    if [ -x "$MACOS_DIR/OpenDeskCastBin" ]; then
        exec "$MACOS_DIR/OpenDeskCastBin" "$APP_DIR/run.py" "$@"
    fi
    exec "$VENV_DIR/bin/python" "$APP_DIR/run.py" "$@"
fi

# 5. Se abbiamo compilato il Mach-O nativo OpenDeskCast, eseguilo direttamente in-process
if file "$MACOS_DIR/OpenDeskCast" 2>/dev/null | grep -q "Mach-O"; then
    exec "$MACOS_DIR/OpenDeskCast" "$@"
fi

# 6. Fallback Mach-O firmato dentro Contents/MacOS/OpenDeskCastBin (per Mac senza Xcode CLT)
export PYTHONHOME="$PY_HOME"
export PYTHONPATH="$APP_DIR:$PY_PATH"
export OPENDESKCAST_SITE_PACKAGES="$PY_SITE"
export PYTHONUTF8="1"
unset __PYVENV_LAUNCHER__
if [ -x "$MACOS_DIR/OpenDeskCastBin" ]; then
    exec "$MACOS_DIR/OpenDeskCastBin" "$APP_DIR/run.py" "$@"
fi

exec "$VENV_DIR/bin/python" "$APP_DIR/run.py" "$@"
"""


INSTALLER_COMMAND_SH = r"""#!/usr/bin/env bash
# OpenDeskCast — Installazione Guidata 1-Click per macOS
set -e

clear
echo "================================================================"
echo "  OpenDeskCast — Installazione e Configurazione Guidata macOS"
echo "================================================================"
echo ""

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_APP="$SRC_DIR/OpenDeskCast.app"
DEST_APP="/Applications/OpenDeskCast.app"

if [ ! -d "$SRC_APP" ] && [ -d "$DEST_APP" ]; then
    SRC_APP="$DEST_APP"
fi

if [ ! -d "$SRC_APP" ]; then
    echo "Errore: OpenDeskCast.app non trovato nella cartella corrente."
    read -r -p "Premi Invio per chiudere..."
    exit 1
fi

echo "[1/4] Rimozione blocco Gatekeeper macOS (xattr -cr)..."
/usr/bin/xattr -cr "$SRC_APP" 2>/dev/null || true

echo "[2/4] Installazione di OpenDeskCast in /Applications..."
if [ "$SRC_APP" != "$DEST_APP" ]; then
    rm -rf "$DEST_APP" 2>/dev/null || true
    cp -R "$SRC_APP" "$DEST_APP"
fi
/usr/bin/xattr -cr "$DEST_APP" 2>/dev/null || true
chmod -R u+rwX "$DEST_APP" 2>/dev/null || true
chmod 755 "$DEST_APP/Contents/MacOS/OpenDeskCast" 2>/dev/null || true
chmod 755 "$DEST_APP/Contents/Resources/bootstrap_macos.sh" 2>/dev/null || true

echo "[3/4] Configurazione ambiente e firma permessi Registrazione Schermo..."
/bin/bash "$DEST_APP/Contents/Resources/bootstrap_macos.sh" --setup-only

echo "[4/4] Avvio di OpenDeskCast..."
/usr/bin/open -a "$DEST_APP"

echo ""
echo "================================================================"
echo "  Installazione completata!"
echo "  NOTA IMPORTANTE PER MACOS:"
echo "  Quando si apre la finestra di regia, clicca sul pulsante"
echo "  guidato per attivare 'OpenDeskCast' in:"
echo "  Impostazioni di Sistema -> Privacy e sicurezza -> Registrazione schermo"
echo "================================================================"
sleep 2
exit 0
"""


def create_macos_app_zip() -> Path:
    version = read_version()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    out_zip = DIST_DIR / f"OpenDeskCast-v{version}-macos.zip"

    print(f"=== [macOS] Creazione pacchetto nativo OpenDeskCast.app (v{version}) ===")

    launcher_sh = (
        "#!/usr/bin/env bash\n"
        'exec /bin/bash "$(cd "$(dirname "$0")/../Resources" && pwd)/bootstrap_macos.sh" "$@"\n'
    ).encode("utf-8")

    info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>OpenDeskCast</string>
    <key>CFBundleDisplayName</key>
    <string>OpenDeskCast</string>
    <key>CFBundleIdentifier</key>
    <string>com.opendeskcast.app</string>
    <key>CFBundleVersion</key>
    <string>{version}</string>
    <key>CFBundleShortVersionString</key>
    <string>{version}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>OpenDeskCast</string>
    <key>CFBundleIconFile</key>
    <string>opendeskcast.icns</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSScreenCaptureUsageDescription</key>
    <string>OpenDeskCast richiede l'accesso alla registrazione dello schermo per trasmettere il display e le finestre aperte ai tuoi dispositivi.</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>OpenDeskCast richiede l'accesso all'audio per trasmettere l'audio del computer.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>OpenDeskCast utilizza AppleScript per controllare l'audio di sistema.</string>
</dict>
</plist>
""".replace("\r\n", "\n").encode("utf-8")

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        now = time.localtime(time.time())[:6]

        def add_dir(arc_path: str) -> None:
            zi = zipfile.ZipInfo(f"{arc_path}/", now)
            zi.create_system = 3  # UNIX permissions preserved by macOS Archive Utility
            zi.external_attr = (stat.S_IFDIR | 0o755) << 16
            zf.writestr(zi, b"")

        def add_file(arc_path: str, data: bytes, is_exec: bool = False, normalize_lf: bool = False) -> None:
            if normalize_lf:
                data = data.replace(b"\r\n", b"\n")
            zi = zipfile.ZipInfo(arc_path, now)
            zi.create_system = 3  # UNIX permissions preserved by macOS Archive Utility
            mode = 0o755 if is_exec else 0o644
            zi.external_attr = (stat.S_IFREG | mode) << 16
            zf.writestr(zi, data)

        # 1-Click Guided macOS Installer script right next to OpenDeskCast.app
        add_file(
            "Installa OpenDeskCast.command",
            INSTALLER_COMMAND_SH.encode("utf-8"),
            is_exec=True,
            normalize_lf=True,
        )

        # Base directories
        add_dir("OpenDeskCast.app")
        add_dir("OpenDeskCast.app/Contents")
        add_dir("OpenDeskCast.app/Contents/MacOS")
        add_dir("OpenDeskCast.app/Contents/Resources")
        add_dir("OpenDeskCast.app/Contents/Resources/app")
        add_dir("OpenDeskCast.app/Contents/Resources/static")

        # Info.plist
        add_file("OpenDeskCast.app/Contents/Info.plist", info_plist)

        # Executable launcher & macOS native Mach-O bootstrap
        add_file("OpenDeskCast.app/Contents/MacOS/OpenDeskCast", launcher_sh, is_exec=True, normalize_lf=True)
        add_file(
            "OpenDeskCast.app/Contents/Resources/bootstrap_macos.sh",
            BOOTSTRAP_MACOS_SH.encode("utf-8"),
            is_exec=True,
            normalize_lf=True,
        )
        add_file(
            "OpenDeskCast.app/Contents/Resources/macos_launcher.c",
            MACOS_LAUNCHER_C.encode("utf-8"),
            is_exec=False,
            normalize_lf=True,
        )

        # Icon
        icns_file = ROOT / "opendeskcast.icns"
        if icns_file.is_file():
            add_file("OpenDeskCast.app/Contents/Resources/opendeskcast.icns", icns_file.read_bytes())
            add_file("OpenDeskCast.app/Contents/Resources/icon.icns", icns_file.read_bytes())

        # App modules
        app_dir = ROOT / "app"
        for pyf in sorted(app_dir.glob("*.py")):
            add_file(
                f"OpenDeskCast.app/Contents/Resources/app/{pyf.name}",
                pyf.read_bytes(),
                normalize_lf=True,
            )

        # Static assets
        static_dir = ROOT / "static"
        for sf in sorted(static_dir.iterdir()):
            if sf.is_file():
                add_file(f"OpenDeskCast.app/Contents/Resources/static/{sf.name}", sf.read_bytes())

        # Root files
        for rf in ("run.py", "VERSION", "LICENSE", "README.md", "requirements.txt", "run_macos.sh"):
            rf_path = ROOT / rf
            if rf_path.is_file():
                is_ex = rf.endswith(".sh")
                add_file(
                    f"OpenDeskCast.app/Contents/Resources/{rf}",
                    rf_path.read_bytes(),
                    is_exec=is_ex,
                    normalize_lf=True,
                )

    print(f"[macOS] Pacchetto creato con successo: {out_zip} ({out_zip.stat().st_size // 1024} KB)")
    return out_zip


if __name__ == "__main__":
    create_macos_app_zip()

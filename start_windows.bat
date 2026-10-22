@echo off
setlocal
cd /d "%~dp0"

:: 1. Se OpenDeskCast.exe esiste, avvialo direttamente
if exist "OpenDeskCast.exe" (
    start "" "OpenDeskCast.exe"
    exit /b 0
)

:: 2. Se manca OpenDeskCast.exe, prova a compilarlo
if exist "launcher.cs" (
    set "CSC="
    if exist "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" set "CSC=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if not defined CSC if exist "C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe" set "CSC=C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
    if defined CSC (
        "%CSC%" /nologo /target:winexe /out:OpenDeskCast.exe /win32icon:opendeskcast.ico /r:System.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll launcher.cs >nul 2>nul
        if exist "OpenDeskCast.exe" (
            start "" "OpenDeskCast.exe"
            exit /b 0
        )
    )
)

:: 3. Fallback: avvia tramite ambiente Python .venv o di sistema
if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" run.py
    exit /b 0
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" python run.py
    exit /b 0
)

echo [ERRORE] OpenDeskCast.exe o Python non trovati.
echo Esegui prima install_windows.bat per completare l'installazione.
echo oppure scarica la versione pronta da https://github.com/marco996/OpenDeskCast/releases/latest
pause
exit /b 1

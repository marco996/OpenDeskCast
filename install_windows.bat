@echo off
setlocal enabledelayedexpansion
title OpenDeskCast — Installazione Guidata Windows

echo ========================================================
echo   OpenDeskCast — Installazione e Configurazione Windows
echo ========================================================
echo.

:: 1. Verifica presenza di Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERRORE] Python 3 non e' stato trovato nel sistema.
    echo Per usare OpenDeskCast senza installare Python, scarica il pacchetto pronto
    echo precompilato da: https://github.com/marco996/OpenDeskCast/releases/latest
    echo.
    echo Altrimenti installa Python da https://www.python.org/ (ricorda di spuntare "Add python.exe to PATH").
    echo.
    pause
    exit /b 1
)

:: 2. Compilazione Launcher C# nativo se mancante
if not exist "OpenDeskCast.exe" (
    echo [1/4] Compilazione interfaccia nativa OpenDeskCast.exe...
    set "CSC="
    if exist "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" set "CSC=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if not defined CSC if exist "C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe" set "CSC=C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
    
    if defined CSC (
        "%CSC%" /nologo /target:winexe /out:OpenDeskCast.exe /win32icon:opendeskcast.ico /r:System.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll launcher.cs
        if %ERRORLEVEL% neq 0 (
            echo [ATTENZIONE] Compilazione csc fallita, verra' usato lo script di avvio.
        ) else (
            echo      Compilazione completata con successo.
        )
    ) else (
        echo [INFO] Compilatore C# non trovato, verra' usato lo script di avvio diretto.
    )
) else (
    echo [1/4] OpenDeskCast.exe gia' presente.
)

:: 3. Creazione virtual environment isolato (.venv)
if not exist ".venv\Scripts\python.exe" (
    echo [2/4] Creazione ambiente isolato (.venv)...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERRORE] Impossibile creare l'ambiente virtuale .venv.
        pause
        exit /b 1
    )
) else (
    echo [2/4] Ambiente .venv gia' configurato.
)

:: 4. Installazione dipendenze
echo [3/4] Installazione dipendenze da requirements.txt...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>nul
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERRORE] Installazione delle dipendenze fallita.
    pause
    exit /b 1
)

:: 5. Creazione collegamenti sul Desktop e Menu Start
echo [4/4] Creazione collegamenti sul Desktop e Menu Start...
set "TARGET_EXE=%~dp0OpenDeskCast.exe"
if not exist "%TARGET_EXE%" set "TARGET_EXE=%~dp0start_windows.bat"
set "ICON_PATH=%~dp0opendeskcast.ico"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut(\"$d\OpenDeskCast.lnk\"); $s.TargetPath = '%TARGET_EXE%'; $s.WorkingDirectory = '%~dp0'; if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%' }; $s.Save(); $sm = [Environment]::GetFolderPath('Programs'); $s2 = $ws.CreateShortcut(\"$sm\OpenDeskCast.lnk\"); $s2.TargetPath = '%TARGET_EXE%'; $s2.WorkingDirectory = '%~dp0'; if (Test-Path '%ICON_PATH%') { $s2.IconLocation = '%ICON_PATH%' }; $s2.Save();"

echo.
echo ========================================================
echo   Installazione completata con successo!
echo   Puoi avviare OpenDeskCast dal collegamento sul Desktop
echo   oppure facendo doppio clic su OpenDeskCast.exe
echo ========================================================
echo.
pause

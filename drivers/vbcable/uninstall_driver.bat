@echo off
setlocal
cd /d "%~dp0"

set "MARKER=%LOCALAPPDATA%\OpenDeskCast\.driver_installed_by_app"
set "MARKER2=%~dp0.installed_by_opendeskcast"

:: Check if OpenDeskCast installed the driver
set "INSTALLED="
if exist "%MARKER%" set "INSTALLED=1"
if exist "%MARKER2%" set "INSTALLED=1"

for /f "tokens=3" %%A in ('reg query "HKCU\Software\OpenDeskCast" /v "DriverInstalledByApp" 2^>nul') do (
    if "%%A"=="0x1" set "INSTALLED=1"
)

:: If not installed by OpenDeskCast, exit immediately without touching the driver
if not defined INSTALLED exit /b 0

:: Uninstall VB-CABLE driver silently with elevation
if exist "VBCABLE_Setup_x64.exe" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~dp0VBCABLE_Setup_x64.exe' -ArgumentList '-u -h' -Verb RunAs -Wait" >nul 2>nul
)

:: Clean up marker flags and registry
if exist "%MARKER%" del /f /q "%MARKER%" >nul 2>nul
if exist "%MARKER2%" del /f /q "%MARKER2%" >nul 2>nul
reg delete "HKCU\Software\OpenDeskCast" /v "DriverInstalledByApp" /f >nul 2>nul

exit /b 0

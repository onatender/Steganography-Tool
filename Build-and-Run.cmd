@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-pyqt.ps1"
if errorlevel 1 (
    echo.
    echo Setup or build failed. Check the error message above.
    pause
    exit /b 1
)
start "" "%~dp0dist\BuryIt.exe"

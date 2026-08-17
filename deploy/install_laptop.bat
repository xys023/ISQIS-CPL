@echo off
REM ============================================================
REM Pastry Quality Inspection System - Windows Installer
REM Requires: Windows 10/11, Python 3.9+ (Add to PATH during install)
REM ============================================================
echo ==============================================
echo   Pastry Quality Inspection - Install
echo ==============================================
echo.

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Install Python 3.9+ from https://www.python.org/downloads/
    echo Check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
python --version
echo.

echo [2/4] Creating virtual environment...
cd /d "%~dp0\.."
if not exist venv (
    python -m venv venv
    echo   Done.
) else (
    echo   Already exists.
)
echo.

echo [3/4] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Install failed. Check network and retry.
    pause
    exit /b 1
)
echo   Done.
echo.

echo [4/4] Creating data directories...
if not exist data\snapshots mkdir data\snapshots
if not exist data\logs mkdir data\logs
if not exist data\models mkdir data\models
echo   Done.
echo.

echo ==============================================
echo   Installation Complete!
echo ==============================================
echo.
echo Start: double-click start_windows.bat
echo Demo (no camera): python run.py --demo
echo Browser: http://localhost:8080
echo.
pause

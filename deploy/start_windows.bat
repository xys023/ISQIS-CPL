@echo off
REM ============================================================
REM Pastry Quality Inspection System - Windows Startup
REM ============================================================
cd /d "%~dp0\.."
REM Ensure Python uses UTF-8 for console output on Windows
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
echo Starting Pastry Quality Inspection System...
echo.
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
python run.py %*
if errorlevel 1 (
    echo.
    echo [Error] Startup failed. Common fixes:
    echo   1. Run install_laptop.bat first
    echo   2. Ensure Python 3.9+ is in PATH
    echo   3. Use: python run.py --demo  (if no camera)
)
echo.
pause

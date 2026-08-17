# ============================================================
# Pastry Quality Inspection System - PowerShell Startup
# Recommended for Windows 10/11 (better UTF-8 support)
# Right-click -> "Run with PowerShell"
# ============================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

# Ensure UTF-8 output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Write-Host "Starting Pastry Quality Inspection System..." -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment if exists
$VenvActivate = Join-Path $ProjectDir "venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    & $VenvActivate
}

# Run the system
try {
    python run.py $args
} catch {
    Write-Host ""
    Write-Host "[Error] Startup failed: $_" -ForegroundColor Red
    Write-Host "Common fixes:" -ForegroundColor Yellow
    Write-Host "  1. Run install_laptop.bat first to install dependencies"
    Write-Host "  2. Ensure Python 3.9+ is installed and in PATH"
    Write-Host "  3. Use: python run.py --demo  (if no camera available)"
    Write-Host ""
    Read-Host "Press Enter to exit"
}

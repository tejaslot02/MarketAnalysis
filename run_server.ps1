[CmdletBinding()]
param (
    [int]$Port = 8080
)

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  NSE India Option Chain and Quantitative Analytics Terminal" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python availability
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python is not installed or not in your system PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/ and try again." -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment if present
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "[*] Activating virtual environment (.venv)..." -ForegroundColor Green
    & .venv\Scripts\Activate.ps1
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[*] Activating virtual environment (venv)..." -ForegroundColor Green
    & venv\Scripts\Activate.ps1
}

Write-Host "[*] Starting Web UI Server on http://127.0.0.1:$Port/" -ForegroundColor Green
Write-Host "[*] Opening default web browser..." -ForegroundColor Green
Write-Host ""

# Launch default browser
Start-Process "http://127.0.0.1:$Port/"

# Start server
python server.py --port $Port

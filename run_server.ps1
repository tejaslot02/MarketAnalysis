[CmdletBinding()]
param (
    [int]$Port = 8080,
    [string]$HostAddress = "127.0.0.1",
    [ValidateSet("sample", "nse")]
    [string]$Provider = "sample",
    [switch]$NoBrowser
)

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  NSE India Option Chain & Options Strategy Intelligence Terminal" -ForegroundColor Cyan
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

Write-Host "[*] Starting Web UI Server on http://${HostAddress}:$Port/ [Provider: $Provider]..." -ForegroundColor Green
if (-not $NoBrowser) {
    Write-Host "[*] Browser will open automatically once the server is ready..." -ForegroundColor Green
}
Write-Host ""

$argsList = @("--port", $Port, "--host", $HostAddress, "--provider", $Provider)
if (-not $NoBrowser) {
    $argsList += "--open"
}

python server.py @argsList

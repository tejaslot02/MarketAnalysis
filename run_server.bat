@echo off
setlocal enabledelayedexpansion

title NSE Option Analytics Terminal Server

echo ==============================================================================
echo   NSE India Option Chain & Quantitative Analytics Terminal
echo ==============================================================================
echo.

:: Check Python availability
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

:: Activate virtual environment if present
if exist ".venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment (venv)...
    call venv\Scripts\activate.bat
)

:: Port configuration (default: 8080 or pass as first argument)
set PORT=8080
if not "%~1"=="" set PORT=%~1

echo [*] Starting Web UI Server on http://127.0.0.1:%PORT%/
echo [*] Launching browser automatically...
echo.

:: Launch browser in background after server starts
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:%PORT%/"

:: Start server
python server.py --port %PORT%

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Server exited unexpectedly with code %ERRORLEVEL%.
    pause
)

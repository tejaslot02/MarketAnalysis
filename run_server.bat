@echo off
setlocal

title NSE Options Strategy Intelligence & Analytics Terminal

echo ==============================================================================
echo   NSE India Option Chain & Options Strategy Intelligence Terminal
echo ==============================================================================
echo.

rem Check Python availability
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

rem Activate virtual environment if present
if exist ".venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment .venv ...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment venv ...
    call venv\Scripts\activate.bat
)

rem Port and argument handling
if "%~1"=="" (
    set "PORT=8080"
    echo [*] Starting Web UI Server on http://127.0.0.1:8080/ [Default Sample Mode]
    echo [*] Browser will open automatically once the server is ready...
    echo.
    python server.py --port 8080 --open
) else (
    rem Check if first argument is a flag (starts with --)
    set "FIRST_ARG=%~1"
    if "%FIRST_ARG:~0,2%"=="--" (
        echo [*] Starting Web UI Server with custom arguments: %*
        echo.
        python server.py %*
    ) else (
        set "PORT=%~1"
        shift
        echo [*] Starting Web UI Server on http://127.0.0.1:%PORT%/
        echo [*] Browser will open automatically once the server is ready...
        echo.
        python server.py --port %PORT% --open %1 %2 %3 %4 %5
    )
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Server exited with status code %ERRORLEVEL%.
    pause
)

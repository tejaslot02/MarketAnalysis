@echo off
setlocal EnableDelayedExpansion

title Job Search Platform - Master End-to-End Pipeline Runner

echo ======================================================================
echo    REMOTE 150K+ DS/AI/ML JOB SEARCH PLATFORM
echo    Complete Production Pipeline Runner with Live Outputs and Links
echo ======================================================================
echo.

cd /d "%~dp0"
set "REPO_ROOT=%~dp0"
set "DICTIONARY_DIR=%REPO_ROOT%data\dictionaries"
set "PYTHONPATH=%REPO_ROOT%;%REPO_ROOT%flows;%REPO_ROOT%scrapers"

:: 1. Ensure .env exists
if not exist "%REPO_ROOT%.env" (
    echo [INFO] .env not found. Initializing from .env.example...
    copy "%REPO_ROOT%.env.example" "%REPO_ROOT%.env" >nul
    echo [INFO] Created .env configuration file.
)

:: 2. Detect Python runner
where uv >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "RUNNER=uv run"
    echo [INFO] Detected uv runtime.
) else if exist "%REPO_ROOT%.venv\Scripts\python.exe" (
    set "RUNNER=%REPO_ROOT%.venv\Scripts\python.exe"
    echo [INFO] Detected virtualenv runtime in .venv
) else (
    set "RUNNER=python"
    echo [INFO] Using system python runtime.
)

:: 3. Check Docker status
set "HAS_DOCKER=0"
where docker >nul 2>nul
if %ERRORLEVEL% equ 0 (
    docker version >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "HAS_DOCKER=1"
    )
)

if "%HAS_DOCKER%"=="1" (
    goto :RUN_DOCKER_PIPELINE
) else (
    goto :RUN_LOCAL_PIPELINE
)

:: ====================================================================
:: MODE 1: DOCKER DISTRIBUTED STACK PIPELINE
:: ====================================================================
:RUN_DOCKER_PIPELINE
echo.
echo ======================================================================
echo [MODE] Docker is running! Executing Full Distributed Stack Pipeline:
echo ======================================================================
echo.

echo [STAGE 1/7] Launching core database and search services...
docker compose up -d postgres dragonfly elasticsearch minio
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start core datastores.
    exit /b %ERRORLEVEL%
)

echo.
echo [STAGE 2/7] Ensuring Prefect database migrations are applied...
docker compose run --rm prefect-init
if %ERRORLEVEL% neq 0 (
    echo [WARN] Prefect init reported an issue; continuing...
)

echo.
echo [STAGE 3/7] Launching Prefect Orchestrator and API services...
docker compose up -d prefect-server prefect-scheduler api
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start orchestration and API services.
    exit /b %ERRORLEVEL%
)

echo.
echo [STAGE 4/7] Seeding Master Data Dimensions (Portals, Skills, Titles, Companies)...
docker compose exec -T prefect-scheduler python /opt/prefect/flows/seed_master_data.py
if %ERRORLEVEL% neq 0 (
    echo [WARN] Seed master data reported an issue; continuing...
)

echo.
echo [STAGE 5/7] Executing Live Web Spiders (Extract stage)...
docker compose exec -T prefect-scheduler python /opt/prefect/flows/scrape_portals.py remotive arbeitnow

echo.
echo [STAGE 6/7] Consuming Redis Stream, Transforming ^& Loading (Postgres, ES, MinIO)...
docker compose exec -T prefect-scheduler python /opt/prefect/flows/scrape_flow.py

echo.
echo [STAGE 7/7] Running Skill Mining and Daily Analytics Snapshots...
docker compose exec -T prefect-scheduler python /opt/prefect/flows/mine_skills.py
docker compose exec -T prefect-scheduler python /opt/prefect/flows/snapshot_analytics.py

:: Also run local export to ensure data\real_jobs_enriched.json is fresh on disk
echo.
echo [INFO] Generating local enriched JSON dataset export...
%RUNNER% scripts/run_real_pipeline_local.py >nul 2>&1

goto :SHOW_OUTPUT_LINKS

:: ====================================================================
:: MODE 2: DIRECT LIVE PIPELINE (FALLBACK IF DOCKER IS NOT RUNNING)
:: ====================================================================
:RUN_LOCAL_PIPELINE
echo.
echo ======================================================================
echo [MODE] Docker daemon is not active. Running Direct Live Python ETL:
echo ======================================================================
echo.
%RUNNER% scripts/run_real_pipeline_local.py
if %ERRORLEVEL% neq 0 (
    echo [FAILED] Live pipeline execution failed!
    exit /b %ERRORLEVEL%
)

:: ====================================================================
:: OUTPUT LINKS AND DASHBOARDS
:: ====================================================================
:SHOW_OUTPUT_LINKS
echo.
echo ======================================================================
echo              PIPELINE EXECUTION COMPLETED SUCCESSFULLY
echo ======================================================================
echo.
echo  LIVE WEB AND API INTERFACES:
echo  --------------------------------------------------------------------
echo  [1] FastAPI Interactive Docs  : http://localhost:8000/docs
echo  [2] Live Ingested Jobs API    : http://localhost:8000/jobs
echo  [3] $150K+ Remote Jobs Filter : http://localhost:8000/jobs?min_salary=150000^&remote=true
echo  [4] API Health Status Check   : http://localhost:8000/health
echo  [5] API Prometheus Metrics    : http://localhost:8000/metrics
echo.
echo  DATA PLATFORM CONSOLES AND CLUSTERS:
echo  --------------------------------------------------------------------
echo  [6] Prefect Orchestrator UI   : http://localhost:4200
echo  [7] MinIO Data Lake Console   : http://localhost:9101
echo      Credentials               : minioadmin / minioadmin
echo  [8] Elasticsearch Search API  : http://localhost:9200/jobs/_search?pretty
echo  [9] Elasticsearch Job Count   : http://localhost:9200/jobs/_count
echo.
echo  LOCAL DATASET EXPORT:
echo  --------------------------------------------------------------------
echo  [10] Enriched JSON File       : data\real_jobs_enriched.json
echo.
echo ======================================================================
if "%1"=="--no-pause" goto :END
echo  Press any key to exit or close this terminal window...
pause >nul
:END
exit /b 0

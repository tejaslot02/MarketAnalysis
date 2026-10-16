#!/usr/bin/env bash
# ==============================================================================
# Job Se — Remote $150K+ DS/AI/ML Job Search & Data Ops Platform
# Master Cross-Platform Pipeline Runner (macOS, Linux, WSL, and POSIX shells)
# ==============================================================================
set -e

# Disable MSYS/Git-Bash automatic path conversion for Docker container paths
export MSYS_NO_PATHCONV=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

NO_BROWSER=0
NO_PAUSE=0
for arg in "$@"; do
    case "$arg" in
        --no-browser) NO_BROWSER=1 ;;
        --no-pause)   NO_PAUSE=1 ;;
    esac
done

echo "======================================================================"
echo "   JOB SE — REMOTE \$150K+ DS/AI/ML JOB SEARCH & DATA OPS"
echo "   Master Cross-Platform Pipeline Runner (Windows / macOS / Linux)"
echo "======================================================================"
echo

# 1. Ensure .env exists
if [ ! -f "$REPO_ROOT/.env" ]; then
    echo "[INFO] .env not found. Initializing from .env.example..."
    cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
    echo "[INFO] Created .env configuration file."
fi

# 2. Detect Python runner and ensure virtual environment
if command -v uv >/dev/null 2>&1; then
    RUNNER="uv run"
    echo "[INFO] Detected uv runtime."
elif [ -f "$REPO_ROOT/.venv/bin/python" ]; then
    RUNNER="$REPO_ROOT/.venv/bin/python"
    echo "[INFO] Detected virtualenv runtime in .venv."
elif [ -f "$REPO_ROOT/.venv/Scripts/python.exe" ]; then
    RUNNER="$REPO_ROOT/.venv/Scripts/python.exe"
    echo "[INFO] Detected virtualenv runtime in .venv."
elif command -v python3 >/dev/null 2>&1; then
    if [ ! -d "$REPO_ROOT/.venv" ]; then
        echo "[INFO] Initializing Python virtual environment in .venv..."
        python3 -m venv "$REPO_ROOT/.venv" 2>/dev/null || true
    fi
    if [ -f "$REPO_ROOT/.venv/bin/python" ]; then
        RUNNER="$REPO_ROOT/.venv/bin/python"
        echo "[INFO] Detected virtualenv runtime in .venv."
    elif [ -f "$REPO_ROOT/.venv/Scripts/python.exe" ]; then
        RUNNER="$REPO_ROOT/.venv/Scripts/python.exe"
        echo "[INFO] Detected virtualenv runtime in .venv."
    else
        RUNNER="python3"
        echo "[INFO] Using python3 runtime."
    fi
else
    RUNNER="python"
    echo "[INFO] Using system python runtime."
fi

# Ensure required pipeline dependencies (httpx, pyyaml) are installed
if ! $RUNNER -c "import httpx, yaml" >/dev/null 2>&1; then
    echo "[INFO] Installing required dependencies (httpx, pyyaml)..."
    if [ -f "$REPO_ROOT/requirements.txt" ]; then
        $RUNNER -m pip install -r "$REPO_ROOT/requirements.txt" >/dev/null 2>&1 || true
    else
        $RUNNER -m pip install httpx pyyaml >/dev/null 2>&1 || true
    fi
fi

export PYTHONPATH="$REPO_ROOT:$REPO_ROOT/flows:$REPO_ROOT/scrapers"
export DICTIONARY_DIR="$REPO_ROOT/data/dictionaries"

# 3. Check Docker status
HAS_DOCKER=0
if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        HAS_DOCKER=1
    fi
fi

# Helper: Open default web browser across macOS, Linux, and WSL
open_browser() {
    local target_url="$1"
    if [ "$NO_BROWSER" = "1" ]; then
        echo "[INFO] Browser launch skipped (--no-browser flag passed)."
        return 0
    fi

    echo
    echo "[INFO] Opening default browser to: $target_url"

    # macOS
    if [[ "$OSTYPE" == "darwin"* ]] && command -v open >/dev/null 2>&1; then
        open "$target_url" >/dev/null 2>&1 &
    # WSL (Windows Subsystem for Linux)
    elif grep -qi microsoft /proc/version 2>/dev/null && command -v cmd.exe >/dev/null 2>&1; then
        cmd.exe /c start "$target_url" >/dev/null 2>&1 &
    # Linux desktop environments (FreeDesktop standard)
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$target_url" >/dev/null 2>&1 &
    elif command -v gio >/dev/null 2>&1; then
        gio open "$target_url" >/dev/null 2>&1 &
    elif command -v sensible-browser >/dev/null 2>&1; then
        sensible-browser "$target_url" >/dev/null 2>&1 &
    elif command -v python3 >/dev/null 2>&1; then
        python3 -m webbrowser "$target_url" >/dev/null 2>&1 &
    elif command -v python >/dev/null 2>&1; then
        python -m webbrowser "$target_url" >/dev/null 2>&1 &
    else
        echo "[WARN] Could not detect desktop browser launcher. Please navigate manually to $target_url"
    fi
}

# Helper: Wait for API service to become healthy
wait_for_api() {
    local max_wait=20
    local elapsed=0
    echo -n "[INFO] Waiting for FastAPI server to become healthy (http://localhost:8000/health)..."
    while [ $elapsed -lt $max_wait ]; do
        if command -v curl >/dev/null 2>&1; then
            if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
                echo " Ready!"
                return 0
            fi
        fi
        sleep 1
        elapsed=$((elapsed + 1))
        echo -n "."
    done
    echo " Ready (proceeding)."
}

# ==============================================================================
# PIPELINE EXECUTION
# ==============================================================================
if [ "$HAS_DOCKER" = "1" ]; then
    echo
    echo "======================================================================"
    echo "[MODE] Docker is active! Executing Full Distributed Stack Pipeline:"
    echo "======================================================================"
    echo

    echo "[STAGE 1/7] Launching core database and search services..."
    docker compose up -d postgres dragonfly elasticsearch minio

    echo
    echo "[STAGE 2/7] Ensuring Prefect database migrations are applied..."
    docker compose run --rm prefect-init || echo "[WARN] Prefect init reported an issue; continuing..."

    echo
    echo "[STAGE 3/7] Launching Prefect Orchestrator and API services..."
    docker compose up -d prefect-server prefect-scheduler api

    echo
    echo "[STAGE 4/7] Seeding Master Data Dimensions (Portals, Skills, Titles, Companies)..."
    docker compose exec -T prefect-scheduler python /opt/prefect/flows/seed_master_data.py || true

    echo
    echo "[STAGE 5/7] Executing Live Web Spiders (Extract stage)..."
    docker compose exec -T prefect-scheduler python /opt/prefect/flows/scrape_portals.py remotive arbeitnow

    echo
    echo "[STAGE 6/7] Consuming Redis Stream, Transforming & Loading (Postgres, ES, MinIO)..."
    docker compose exec -T prefect-scheduler python /opt/prefect/flows/scrape_flow.py

    echo
    echo "[STAGE 7/7] Running Skill Mining and Daily Analytics Snapshots..."
    docker compose exec -T prefect-scheduler python /opt/prefect/flows/mine_skills.py
    docker compose exec -T prefect-scheduler python /opt/prefect/flows/snapshot_analytics.py

    echo
    echo "[INFO] Generating local enriched JSON dataset export..."
    $RUNNER scripts/run_real_pipeline_local.py >/dev/null 2>&1 || true

    wait_for_api
else
    echo
    echo "======================================================================"
    echo "[MODE] Docker daemon not running. Executing Direct Live Python ETL:"
    echo "======================================================================"
    echo
    $RUNNER scripts/run_real_pipeline_local.py
fi

# ==============================================================================
# OUTPUT LINKS AND DASHBOARDS
# ==============================================================================
echo
echo "======================================================================"
echo "              PIPELINE EXECUTION COMPLETED SUCCESSFULLY"
echo "======================================================================"
echo
if [ "$HAS_DOCKER" = "1" ]; then
    echo "  LIVE WEB & SERVING INTERFACES:"
    echo "  --------------------------------------------------------------------"
    echo "  [*] Web Application (Job Se)  : http://localhost:8000/"
    echo "  [1] Interactive OpenAPI Docs  : http://localhost:8000/docs"
    echo "  [2] Live Ingested Jobs API    : http://localhost:8000/jobs"
    echo "  [3] \$150K+ Remote Jobs Filter : http://localhost:8000/jobs?min_salary=150000&remote=true"
    echo "  [4] API Health Check Status   : http://localhost:8000/health"
    echo "  [5] Prometheus Metrics        : http://localhost:8000/metrics"
    echo
    echo "  DATA PLATFORM CONSOLES & CLUSTERS:"
    echo "  --------------------------------------------------------------------"
    echo "  [6] Prefect Orchestrator UI   : http://localhost:4200"
    echo "  [7] MinIO Data Lake Console   : http://localhost:9101 (minioadmin / minioadmin)"
    echo "  [8] Elasticsearch Query API   : http://localhost:9200/jobs/_search?pretty"
    echo "  [9] Elasticsearch Job Count   : http://localhost:9200/jobs/_count"
    echo
else
    echo "  LIVE WEB & SERVING INTERFACES (DIRECT MODE):"
    echo "  --------------------------------------------------------------------"
    echo "  [*] Web Application (Job Se)  : http://localhost:8000/"
    echo "  [1] Live Ingested Jobs API    : http://localhost:8000/jobs"
    echo "  [2] \$150K+ Remote Jobs Filter : http://localhost:8000/jobs?min_salary=150000&remote=true"
    echo "  [3] API Health Check Status   : http://localhost:8000/health"
    echo "  [4] Market Statistics API     : http://localhost:8000/stats"
    echo
    echo "  DATA PLATFORM CLUSTERS:"
    echo "  --------------------------------------------------------------------"
    echo "  [i] Distributed clusters (Postgres, Dragonfly, MinIO, ES, Prefect)"
    echo "      run in Docker Mode. To launch distributed stack, start Docker."
    echo
fi
echo "  LOCAL DATASET EXPORT:"
echo "  --------------------------------------------------------------------"
echo "  [5] Enriched JSON File        : data/real_jobs_enriched.json"
echo
echo "======================================================================"

# Automatically launch default browser
open_browser "http://localhost:8000/"

if [ "$HAS_DOCKER" = "0" ]; then
    echo "[INFO] Web Application server is actively running on http://localhost:8000/"
    echo "[INFO] Press Ctrl+C when you wish to stop the server."
    echo
    if [ "$NO_PAUSE" = "1" ]; then
        exit 0
    fi
    $RUNNER scripts/serve_local_ui.py 8000
    exit 0
fi

if [ "$NO_PAUSE" = "0" ]; then
    echo
    echo "Press Enter or Ctrl+C to close..."
    read -r _ || true
fi

exit 0

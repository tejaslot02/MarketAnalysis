# Changelog

All notable changes to the **Remote $150K+ DS/AI/ML Job Search Platform** committed to the `UI` branch are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - Branch `UI`

### Added
- **Real-Time Pipeline Telemetry & Live Streaming Log Console** (`e9510c1`):
  - **Embedded Industrial Terminal**: A high-contrast dark-mode terminal (`#0d1117`) inside the Operations Control Plane to monitor worker output and execution telemetry in real time.
  - **Live Prefect Log Ingestion**: Background tasks actively poll Prefect 3's `/api/logs/filter` API during flow execution, streaming worker logs into an in-memory ring buffer (capped at 2,000 entries).
  - **Interactive Log Controls**:
    - Log severity filters (`ALL`, `INFO`, `SUCCESS`, `WARN`, `ERROR`).
    - Substring / keyword search filter with clear button (e.g., `greenhouse`, `ashby`, `jobs=`).
    - Smart auto-scroll toggle with viewport scroll detection and a floating `"↓ New logs incoming • Click to scroll to latest"` prompt.
    - One-click "Copy visible logs" to clipboard with visual confirmation.
    - Fullscreen expansion toggle for terminal debugging.
    - Direct deep-link (`Prefect UI ↗`) linking directly to the active flow run on `http://localhost:4200/runs/flow-run/<flow_run_id>`.
  - **Execution Stepper & Progress Tracker**:
    - Animated striped progress bar tracking completion percentage (0% to 100%).
    - 4-stage stepper grid (`Seed Master Dimensions`, `Web Spiders Extract`, `Stream Ingestion & Multi-Store Load`, `Mining Skill Trends & Snapshots`) with duration timers and status badges.
    - Dynamic DAG node highlighting reflecting live worker states.
  - **New Control Plane Endpoints**:
    - `GET /api/ops/pipeline-logs`: Paginated, filterable real-time log endpoint with fallback to historical Prefect logs.
    - `POST /api/ops/pipeline-logs/clear`: In-memory log buffer flush endpoint.
    - `GET /api/ops/pipeline-status`: Enhanced telemetry response with stages array, active flow run ID, progress percentage, and elapsed timers.

- **Standalone Local Web UI Server & Cross-Platform Runners** (`6ae1340`):
  - Added [`scripts/serve_local_ui.py`](file:///e:/Work/job_se/scripts/serve_local_ui.py) for serving the frontend and API locally without requiring full Docker orchestration.
  - Enhanced [`run_all.bat`](file:///e:/Work/job_se/run_all.bat) and [`run_all.sh`](file:///e:/Work/job_se/run_all.sh) with automatic virtual environment verification, port conflict handling, and automated stack healthchecks.

- **Developer-First Web Interface & Ops Control Plane** (`bc89ac6`):
  - Single-Page Application (SPA) frontend in [`api/app/static/`](file:///e:/Work/job_se/api/app/static/):
    - **Job Discovery View**: Full-width job search, strict $\ge\$150\text{K}$ salary filter, seniority filters, interactive slide-out job specification drawer, and semantic match scoring.
    - **Market Insights View**: Dynamic compensation histograms, skill frequency rankings, remote ratio analytics, and hiring company volume.
    - **Control Plane View**: Real-time Dragonfly stream lag monitor, in-flight unacknowledged count, DLQ triage console with payload inspector and batch re-drive.
  - Operations Router [`api/app/routers/ops.py`](file:///e:/Work/job_se/api/app/routers/ops.py):
    - Stream telemetry (`/api/ops/stream-status`).
    - DLQ inspection and replay (`/api/ops/dlq-messages`, `/api/ops/dlq-replay`).
    - Crawler run history (`/api/ops/spider-runs`).
    - Discovered taxonomy promotion (`/api/ops/taxonomy-candidates`, `/api/ops/promote-skill`).
  - Comprehensive documentation suite in [`docs/`](file:///e:/Work/job_se/docs/) (`01-architecture.md` through `09-glossary.md`).

- **Distributed Stack & Master Runner Automation** (`8ff6367`):
  - Automated master execution script [`run_all.bat`](file:///e:/Work/job_se/run_all.bat) orchestrating Dragonfly, PostgreSQL, Elasticsearch, MinIO, Spark, Prefect, and FastAPI.
  - Added pipeline verification scripts:
    - [`scripts/run_real_pipeline_local.py`](file:///e:/Work/job_se/scripts/run_real_pipeline_local.py): Headless local pipeline execution runner.
    - [`scripts/verify_all_pipelines.py`](file:///e:/Work/job_se/scripts/verify_all_pipelines.py): End-to-end integration test validating stream ingestion, DLQ routing, and multi-store persistence.

- **Enterprise GenAI Stack & Modular Monolith Architecture** (`3f13c01`):
  - **Hexagonal Architecture (`core/`)**:
    - Domain entities: `Job`, `Company`, `Salary`, `Skill`.
    - Ports & interfaces: `EmbeddingProvider`, `LLMProvider`, `Reranker`, `VectorStore`, `Cache`.
    - Core domain services: `SkillExtractor`, `SeniorityDetector`, `SalaryNormalizer`, `TitleCanonicalizer`, `ResponsibilityExtractor`.
  - **GenAI Adapters & RAG Pipeline (`ai/`)**:
    - LLM adapters: OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Local vLLM/Ollama.
    - Embedding adapters: OpenAI `text-embedding-3-small`, Sentence-Transformers `all-MiniLM-L6-v2`.
    - Cross-Encoder reranker adapter.
    - Chunking engine: Semantic job description chunker (`JobDescriptionChunker`).
    - Hybrid Retriever: Reciprocal Rank Fusion (RRF) combining dense vector search (Postgres pgvector) and lexical BM25 matching (Elasticsearch).
  - **Guardrails & Evaluation Suite (`ai/guardrails/`, `evals/`)**:
    - Input & output safety guardrails (Prompt Injection defense, PII masking).
    - Prompt regression harness and RAGAS retrieval evaluation suite with golden test sets.
  - **FastAPI Modular Monolith (`api/app/routers/`)**:
    - Refactored monolith into decoupled routers: `health.py`, `jobs.py`, `search.py`, `stats.py`.
    - Dead-Letter Queue handler (`flows/dlq_handler.py`) and pgvector embedding flow (`flows/embed_jobs_flow.py`).

### Fixed
- Resolved duplicate `portal_runs` persistence bug in [`flows/scrape_portals.py`](file:///e:/Work/job_se/flows/scrape_portals.py).
- Added automatic Dragonfly stream trimming in [`scrapers/pipelines.py`](file:///e:/Work/job_se/scrapers/pipelines.py) to prevent unbounded memory growth.
- Corrected Docker dependency build issues in `api/Dockerfile` and `prefect/requirements.txt`.

# Commit-Wise Changelog

> **MANDATE**: Every commit to this repository MUST include an entry in this changelog documenting the commit hash, date, author, affected modules, and a granular breakdown of changes.
> Enforced locally via Git Pre-Commit Hook (`.githooks/pre-commit`) and in CI quality gates.

---

## [Commit ac87e29] — 2026-10-30
- **Commit**: `ac87e29`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `refactor: overhaul repository for modular NSE Option Chain scraping, analytics, and multi-format storage`
- **Affected Files**:
  - [`config/settings.py`](file:///e:/Work/MarketAnalysis/config/settings.py)
  - [`config/__init__.py`](file:///e:/Work/MarketAnalysis/config/__init__.py)
  - [`core/session.py`](file:///e:/Work/MarketAnalysis/core/session.py)
  - [`core/crawler.py`](file:///e:/Work/MarketAnalysis/core/crawler.py)
  - [`core/__init__.py`](file:///e:/Work/MarketAnalysis/core/__init__.py)
  - [`parsers/option_chain.py`](file:///e:/Work/MarketAnalysis/parsers/option_chain.py)
  - [`parsers/__init__.py`](file:///e:/Work/MarketAnalysis/parsers/__init__.py)
  - [`storage/handler.py`](file:///e:/Work/MarketAnalysis/storage/handler.py)
  - [`storage/__init__.py`](file:///e:/Work/MarketAnalysis/storage/__init__.py)
  - [`tests/test_session.py`](file:///e:/Work/MarketAnalysis/tests/test_session.py)
  - [`tests/test_crawler.py`](file:///e:/Work/MarketAnalysis/tests/test_crawler.py)
  - [`tests/test_parser.py`](file:///e:/Work/MarketAnalysis/tests/test_parser.py)
  - [`tests/test_storage.py`](file:///e:/Work/MarketAnalysis/tests/test_storage.py)
  - [`main.py`](file:///e:/Work/MarketAnalysis/main.py)
  - [`requirements.txt`](file:///e:/Work/MarketAnalysis/requirements.txt)
  - [`pyproject.toml`](file:///e:/Work/MarketAnalysis/pyproject.toml)
  - [`Makefile`](file:///e:/Work/MarketAnalysis/Makefile)
  - [`.env.example`](file:///e:/Work/MarketAnalysis/.env.example)
  - [`.gitignore`](file:///e:/Work/MarketAnalysis/.gitignore)
  - [`README.md`](file:///e:/Work/MarketAnalysis/README.md)
  - [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md)
- **Detailed Changes**:
  - **Complete Legacy Purge**:
    - Removed extraneous job search modules, including `ai/`, `api/`, `db/`, `docs/`, `evals/`, `flows/`, `monitoring/`, `notebooks/`, `prefect/`, `prompts/`, `scrapers/`, and `scripts/`.
    - Removed unused docker-compose and runner scripts (`docker-compose.yml`, `run_all.bat`, `run_all.sh`).
  - **Anti-Bot NSE Session Management (`core/session.py`)**:
    - Built `NSESessionManager` implementing two-tier cookie handshake (`base_url` -> polite delay -> `option_chain_page_url`) to acquire Akamai and Cloudflare perimeter security tokens (`_abck`, `ak_bmsc`, `bm_sz`, `bm_sv`, `nsit`).
    - Integrated `curl_cffi` TLS fingerprint impersonation (`chrome124`) with automatic fallback to standard `requests`.
    - Implemented auto-refresh logic recovering seamlessly from `401 Unauthorized` or `403 Forbidden` challenge states.
  - **Resilient Option Chain Crawler (`core/crawler.py`)**:
    - Developed `NSEOptionChainCrawler` featuring exponential backoff with random jitter, polite request delays, and symbol aliasing.
    - Implemented multi-route query strategy: Primary extraction via NSE `NextApi` derivative feed with fallback to classic `option-chain-indices` and `option-chain-equities`.
  - **Quantitative Data Parser (`parsers/option_chain.py`)**:
    - Built `OptionChainParser` converting raw JSON payloads into clean Pandas DataFrames (`calls_df`, `puts_df`, `chain_df`, `futures_df`).
    - Structured unified side-by-side Option Chain Matrix (Call metrics on left, Strike in center, Put metrics on right).
    - Added automated quantitative indicators: At-The-Money (ATM) strike, Max Pain strike, Put-Call Ratio (PCR by OI and Volume), and expiry filtering.
  - **Multi-Format Storage Pipeline (`storage/handler.py`)**:
    - Implemented `StorageHandler` supporting timestamped exports to CSV, compressed Apache Parquet (`snappy`), SQLite database with market snapshot tracking, and raw JSON payload archiving.
  - **CLI Orchestrator & Test Suite (`main.py`, `tests/`)**:
    - Implemented production CLI `main.py` with arguments for symbol, equity flag, expiry filter, storage format selection, market status probe, and formatted console summary.
    - Wrote 11 comprehensive automated tests across all modules (`tests/`).

---

## [Commit d2ac194] — 2026-10-16
- **Commit**: `d2ac194`
- **Message**: `ci(changelog): mandate commit-wise changelog updates via git hook, CI gate, and agent rules`
- **Affected Files**:
  - [`.githooks/pre-commit`](file:///e:/Work/job_se/.githooks/pre-commit)
  - [`.github/workflows/ci.yml`](file:///e:/Work/job_se/.github/workflows/ci.yml)
  - [`.agents/rules/changelog_mandate.md`](file:///e:/Work/job_se/.agents/rules/changelog_mandate.md)
  - [`AGENTS.md`](file:///e:/Work/job_se/AGENTS.md)
  - [`CHANGELOG.md`](file:///e:/Work/job_se/CHANGELOG.md)
- **Detailed Changes**:
  - **Git Pre-Commit Hook**: Created executable pre-commit hook in `.githooks/pre-commit` and activated repository `core.hooksPath` configuration. Blocks any commit if repository files are staged without `CHANGELOG.md`.
  - **CI Workflow Quality Gate**: Added `enforce-changelog` job to `.github/workflows/ci.yml` that validates `CHANGELOG.md` modification on pull requests.
  - **AI Agent & Developer Rules**: Created workspace customization rule `.agents/rules/changelog_mandate.md` and repository guidelines in `AGENTS.md` to guarantee AI assistants maintain commit-wise logs.
  - **Commit-Wise Restructuring**: Re-architected `CHANGELOG.md` into a strictly commit-by-commit hierarchical format.

---

## [Commit c879ac9] — 2026-10-16
- **Commit**: `c879ac9447e17478d227f2df479f60cb0a8f828a`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `docs: add CHANGELOG.md documenting all features and changes on UI branch`
- **Affected Files**: `CHANGELOG.md`
- **Summary**:
  - Initialized repository changelog documenting the cumulative features, fixes, and architecture implementations delivered on the `UI` branch.

---

## [Commit e9510c1] — 2026-10-16
- **Commit**: `e9510c14c8fa10097a2c17725b93e1f2a9f05bf5`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `Add frontend UI components and operational management router for Job SE application`
- **Affected Files**: 
  - [`api/app/routers/ops.py`](file:///e:/Work/job_se/api/app/routers/ops.py)
  - [`api/app/static/index.html`](file:///e:/Work/job_se/api/app/static/index.html)
  - [`api/app/static/css/styles.css`](file:///e:/Work/job_se/api/app/static/css/styles.css)
  - [`api/app/static/js/app.js`](file:///e:/Work/job_se/api/app/static/js/app.js)
- **Detailed Changes**:
  - **Live Log Terminal Console**:
    - Created an embedded industrial dark monospace terminal (`#0d1117`) in the Control Plane view for live Prefect worker log streaming.
    - Added log severity filters: `ALL`, `INFO`, `SUCCESS`, `WARN`, `ERROR`.
    - Added real-time substring search filter with clear button.
    - Added smart auto-scroll with pause-on-scroll detection and floating `"↓ New logs incoming"` jump button.
    - Added one-click clipboard copy of visible log entries and console buffer clear button.
    - Added deep-link button (`Prefect UI ↗`) routing directly to `http://localhost:4200/runs/flow-run/<active_id>`.
    - Added expandable full-screen viewport toggle.
  - **4-Stage Pipeline Progress Stepper**:
    - Built dynamic multi-stage execution tracker (`Seed Dimensions`, `Web Spiders Extract`, `Stream Ingestion & Stores`, `Analytics & Skill Mining`).
    - Added real-time animated striped progress bar (0% to 100%) and elapsed timer.
    - Added dynamic DAG node highlighting and state badges (`Crawling...`, `Sync complete`, `Healthy`).
  - **Backend Log Ingestion Engine**:
    - Implemented in-memory ring-buffered log buffer (`pipeline_logs`, max 2,000 entries) in `ops.py`.
    - Active polling of Prefect 3's `/api/logs/filter` endpoint every 2 seconds during flow execution.
    - Added REST endpoints: `GET /api/ops/pipeline-logs`, `POST /api/ops/pipeline-logs/clear`, and enriched `GET /api/ops/pipeline-status`.
    - Added state persistence so page refreshes seamlessly reconnect to active runs and preserve log history.

---

## [Commit 6ae1340] — 2026-10-16
- **Commit**: `6ae1340a68311e5ef5cddcdcbe37d3215ea98aac`
- **Author**: Tejas `<tejaslot02@gmail.com>`
- **Message**: `Add standalone local web UI server script and enhance runner scripts for virtual environment setup`
- **Affected Files**:
  - [`scripts/serve_local_ui.py`](file:///e:/Work/job_se/scripts/serve_local_ui.py)
  - [`run_all.bat`](file:///e:/Work/job_se/run_all.bat)
  - [`run_all.sh`](file:///e:/Work/job_se/run_all.sh)
  - `requirements.txt`, `requirements-dev.txt`
- **Detailed Changes**:
  - **Standalone UI Server**: Created [`scripts/serve_local_ui.py`](file:///e:/Work/job_se/scripts/serve_local_ui.py) allowing frontend and API testing locally without spinning up the entire Docker cluster.
  - **Automated Environment Provisioning**:
    - Updated Windows batch launcher (`run_all.bat`) and Linux/macOS launcher (`run_all.sh`) to detect and auto-create `.venv`.
    - Automated pip dependency installation from `requirements.txt` and `requirements-dev.txt`.
    - Added port availability pre-flight checks and colored terminal diagnostics.

---

## [Commit bc89ac6] — 2026-10-13
- **Commit**: `bc89ac62ca791c8ef3873e0034b40c57337921b1`
- **Author**: Tejas Lot `<tejaslot02@gmail.com>`
- **Message**: `feat(ui): add developer-first Job Se web interface, ops control plane, cross-platform runner, and documentation`
- **Affected Files**:
  - [`api/app/static/index.html`](file:///e:/Work/job_se/api/app/static/index.html)
  - [`api/app/static/css/styles.css`](file:///e:/Work/job_se/api/app/static/css/styles.css)
  - [`api/app/static/js/app.js`](file:///e:/Work/job_se/api/app/static/js/app.js)
  - [`api/app/routers/ops.py`](file:///e:/Work/job_se/api/app/routers/ops.py)
  - [`api/app/main.py`](file:///e:/Work/job_se/api/app/main.py)
  - [`docs/`](file:///e:/Work/job_se/docs/) (`01-architecture.md` through `09-glossary.md`)
  - `Makefile`, `docker-compose.yml`, `run_all.bat`, `run_all.sh`
- **Detailed Changes**:
  - **Developer-First Single-Page Application**:
    - **Job Discovery View**: Full-width responsive cards, interactive drawer for salary and tech stack breakdown, hybrid vector match scoring, and filters for $\ge\$150\text{K}$ salary and remote status.
    - **Market Insights View**: Analytical histograms for salary distributions, top demanded technical skills, seniority ratios, and hiring company metrics.
    - **Operations Control Plane**: Real-time Dragonfly Redis stream backlog gauges, in-flight unacknowledged metrics, and Dead-Letter Queue (DLQ) triage console with manual re-drive.
  - **Data Operations Router**: Added `ops.py` with endpoints for `/api/ops/stream-status`, `/api/ops/dlq-messages`, `/api/ops/dlq-replay`, `/api/ops/spider-runs`, `/api/ops/taxonomy-candidates`, and `/api/ops/promote-skill`.
  - **Documentation Suite**: Added complete system documentation across 9 manuals covering system architecture, module specifications, data flows, pipeline orchestration, user guides, runbooks, and risk matrices.

---

## [Commit 8ff6367] — 2026-10-13
- **Commit**: `8ff63675b59f0f5c1cd3d4bdcb3f8d74229ef6a5`
- **Author**: Tejas Lot `<tejaslot02@gmail.com>`
- **Message**: `fix(pipeline): resolve distributed stack dependencies, add master run_all.bat with links output`
- **Affected Files**:
  - `api/Dockerfile`, `docker-compose.yml`, `prefect/requirements.txt`, `scrapers/requirements.txt`
  - [`flows/scrape_flow.py`](file:///e:/Work/job_se/flows/scrape_flow.py), [`flows/scrape_portals.py`](file:///e:/Work/job_se/flows/scrape_portals.py)
  - [`scripts/run_real_pipeline_local.py`](file:///e:/Work/job_se/scripts/run_real_pipeline_local.py)
  - [`scripts/verify_all_pipelines.py`](file:///e:/Work/job_se/scripts/verify_all_pipelines.py)
  - `run_all.bat`
- **Detailed Changes**:
  - **Distributed Dependency Resolution**:
    - Fixed asyncpg and psycopg2 driver conflicts in API and Prefect Dockerfiles.
    - Resolved container network dependencies between Dragonfly, Postgres, Elasticsearch, and Prefect.
  - **Pipeline Verification Tools**:
    - Created [`scripts/verify_all_pipelines.py`](file:///e:/Work/job_se/scripts/verify_all_pipelines.py) validating the end-to-end flow: spider scraping $\rightarrow$ Redis stream $\rightarrow$ normalization $\rightarrow$ Postgres/ES/MinIO multi-store sync $\rightarrow$ DLQ routing.
    - Created [`scripts/run_real_pipeline_local.py`](file:///e:/Work/job_se/scripts/run_real_pipeline_local.py) for headless test runs.
  - **Master Orchestration Script**: Added Windows master launcher [`run_all.bat`](file:///e:/Work/job_se/run_all.bat) outputting verified endpoint links for all 8 services.

---

## [Commit 3f13c01] — 2026-10-13
- **Commit**: `3f13c01b0503fddc51c7d9db2df243f38fe5e458`
- **Author**: Tejas Lot `<tejaslot02@gmail.com>`
- **Message**: `refactor: implement Clean Architecture, modular monolith, and enterprise GenAI stack`
- **Affected Files**:
  - `core/` (domain, ports, services)
  - `ai/` (adapters, rag, guardrails, agents)
  - `api/app/routers/` (`health.py`, `jobs.py`, `search.py`, `stats.py`)
  - `flows/dlq_handler.py`, `flows/embed_jobs_flow.py`
  - `evals/`, `prompts/`, `tests/`
- **Detailed Changes**:
  - **Hexagonal Architecture (`core/`)**:
    - Defined domain entities: `Job`, `Company`, `Salary`, `Skill`.
    - Defined interface ports: `EmbeddingProvider`, `LLMProvider`, `Reranker`, `VectorStore`, `Cache`.
    - Created domain services: `SkillExtractor`, `SeniorityDetector`, `SalaryNormalizer`, `TitleCanonicalizer`, `ResponsibilityExtractor`.
  - **Enterprise GenAI & RAG Pipeline (`ai/`)**:
    - Model adapters for OpenAI (GPT-4o, text-embedding-3-small), Anthropic Claude 3.5 Sonnet, and Sentence-Transformers.
    - Added Cross-Encoder reranker adapter.
    - Built hybrid search retriever combining pgvector cosine similarity with Elasticsearch BM25 using Reciprocal Rank Fusion (RRF).
    - Added input/output guardrails for Prompt Injection defense and PII protection.
  - **FastAPI Modular Monolith**:
    - Decoupled `main.py` into dedicated routers: `health.py`, `jobs.py`, `search.py`, `stats.py`.
  - **Quality Gates & Evaluation**:
    - Added prompt regression evaluation harness and RAGAS benchmark datasets.
    - Added Dead-Letter Queue handler (`flows/dlq_handler.py`) and stream trimming in scrapers.

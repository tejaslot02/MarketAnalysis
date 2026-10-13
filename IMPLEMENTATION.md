# Implementation & Architecture Guide

## 1. Executive Summary & Purpose
- **Project Overview:** The **Remote 150K+ DS/AI/ML Job Search Platform** is an enterprise-grade big-data ingestion, enrichment, analytics, and serving platform designed to systematically identify, normalize, and monitor high-compensation ($150,000+ USD annual base or total compensation), remote Data Science, Machine Learning, and Artificial Intelligence roles in the United States market. The system automates the complete data lifecycle—from multi-source web scraping and public Application Tracking System (ATS) harvesting to streaming message ingestion, NLP-based dictionary normalization, vector-ready relational persistence, full-text indexing, object storage archiving, and business intelligence reporting.
- **Core Domain:** 
  - **Job Postings:** Raw unstructured descriptions converted into canonical records featuring standardized titles, compensation bounds, currency, remote status, seniority tiers, extracted technical skills, and key responsibilities.
  - **Companies & ATS Boards:** Company master data tracked across board handles (Greenhouse tokens, Lever slugs, Ashby organizations, and Workable accounts).
  - **Skills & Taxonomies:** Hierarchical technical skill graphs categorized into programming languages, ML/DL frameworks, LLM/GenAI stacks, data engineering, storage/databases, and domain specializations with associated importance weights.
  - **Career Tracks & Titles:** Canonicalization of varied industry titles into standard career tracks (Individual Contributor, MLOps/Platform, Research, Leadership) with verified salary bands.
  - **Crawler Freshness & Observability:** Real-time logging of portal execution runs, job counts emitted, errors, and crawler performance.
  - **Market Analytics & Skill Mining:** Longitudinal daily snapshots of market trends, skill momentum, company hiring velocity, and unsupervised extraction of emerging technical terminology.

---

## 2. Technology Stack & Dependencies
- **Core Languages & Runtimes:**
  - **Python 3.11:** Primary runtime for the FastAPI application service and Scrapy crawlers (`python:3.11-slim`).
  - **Python 3.12:** Execution runtime for Prefect orchestration and ETL flows (`prefecthq/prefect:3.2.14-python3.12`).
  - **Java 17 (OpenJDK):** Underlying JVM execution engine for Apache Spark 3.5.9.
- **Frameworks & Libraries:**
  - **Web API:** FastAPI `0.111.0`, Uvicorn `0.30.1`, Pydantic `2.7.4`.
  - **Crawling & Scraping:** Scrapy `2.11.2`, Twisted `23.10.0`, BeautifulSoup4 `4.12.3`, lxml `5.2.2`, Requests `2.32.3`.
  - **Orchestration:** Prefect `3.2.14` (`prefect.serve` deployment engine).
  - **Database Connectivity & ORM:** SQLAlchemy `2.0.31`, `psycopg2-binary 2.9.9` (synchronous API access), `asyncpg >= 0.29.0` (asynchronous pipeline flows), `pgvector 0.2.5`.
  - **Distributed Processing:** Apache Spark `3.5.9-python3` (Master and Worker nodes), PySpark notebook environment (`spark-3.5.0`).
  - **Configuration & Utilities:** PyYAML `6.0.1`, python-dateutil `2.9.0.post0`.
- **Infrastructure & Storage:**
  - **Relational & Vector DB:** PostgreSQL 16 via Docker image `pgvector/pgvector:pg16` with native HNSW vector index support.
  - **Search Engine:** Elasticsearch `8.13.4` (single-node cluster, client library `8.13.2`) for full-text search and faceted filtering.
  - **Message Broker & In-Memory Store:** Dragonfly `v2.0.0` (multi-threaded, Redis-compatible engine on port 6379/6380) utilized for both rate-limiting/caching and high-throughput Redis Streams (`XADD`, `XREADGROUP`, `XAUTOCLAIM`). Python client: `redis 5.0.8`.
  - **Object Storage / Data Lake:** MinIO (`RELEASE.2025-07-23T15-54-02Z`, client `minio 7.2.7`) for immutable raw JSON archiving and future Parquet batch layers.
  - **Analytics & BI:** Metabase `v0.49.13` (backed by PostgreSQL application database).
- **Development & Tooling:**
  - **Testing:** Pytest `8.2.2`.
  - **Monitoring & Metrics:** Prometheus `v2.52.0` (scraping Prefect and FastAPI endpoints), `prometheus_client 0.20.0`.
  - **Visualization:** Grafana `10.4.3` with provisioned Prometheus and PostgreSQL datasources, along with pre-built ETL and market dashboards.
  - **Containerization:** Docker Compose v2 (`job-search` project).

---

## 3. Architecture & System Design
- **Architectural Pattern:** **Decoupled Event-Driven Ingestion with Medallion / Multi-Tier Storage**.
  - **Extract (Producers):** Independent Scrapy spiders fan out across ATS public APIs and web portals, producing canonical job dictionaries and streaming them via Redis Streams into Dragonfly.
  - **Buffer / Queue:** Dragonfly Redis Streams (`raw-jobs`) decouple variable web scraping ingestion bursts from database persistence.
  - **Transform & Load (Consumers):** Prefect workflow consumers (`consume-raw-jobs`) pull stream batches, apply pure-function YAML dictionary transformations, and distribute records simultaneously into PostgreSQL (system of record), Elasticsearch (search index), and MinIO (raw data lake).
  - **Serve & Analyze:** FastAPI provides low-latency REST endpoints; Metabase provides operational dashboards; Jupyter connects directly to Spark and PostgreSQL for ad-hoc analysis.

```
                              +---------------------------------------+
                              |      Target Portals & ATS Boards       |
                              |  (Greenhouse, Ashby, RemoteOK, etc.)   |
                              +---------------------------------------+
                                                  |
                                                  | HTTP / JSON API / Scrape
                                                  v
                                      +-----------------------+
                                      |    Scrapy Spiders     |
                                      |  (scrapers/portals/)  |
                                      +-----------------------+
                                                  |
                                                  | XADD (stream: raw-jobs)
                                                  v
                                      +-----------------------+
                                      |       Dragonfly       |
                                      |     Redis Streams     |
                                      +-----------------------+
                                                  |
                                                  | XREADGROUP / XAUTOCLAIM
                                                  v
                                      +-----------------------+
                                      |   Prefect ETL Flow    |
                                      | (flows/scrape_flow.py)|
                                      +-----------------------+
                                      /           |           \
                    Postgres Upsert  /            | Index Doc  \  Put Object (JSON)
                                    v             v             v
                     +-------------------+  +-----------+  +---------------+
                     | Postgres+pgvector |  | Elastic-  |  |     MinIO     |
                     |   (Master Store)  |  |  search   |  |  (Raw Lake)   |
                     +-------------------+  +-----------+  +---------------+
                            |        |            |                |
                SQL Queries |        | SQL Views  | REST Search    | Parquet/S3A
                            v        v            v                v
                     +----------+  +----------+  +--------+  +-------------+
                     | FastAPI  |  | Metabase |  | Alerts |  | Spark/Jupyter|
                     | (:8000)  |  | (:3001)  |  | Engine |  | (:8080/8888)|
                     +----------+  +----------+  +--------+  +-------------+
```

- **Project Directory Structure:**
```
d:\job_se\
├── .env.example                     # Environment template for ports, credentials, cron schedules
├── docker-compose.yml               # Multi-service infrastructure orchestration (12 containers)
├── Makefile                         # Lifecycle automation (up, down, migrate, seed, test, scrape)
├── requirements-dev.txt             # Local development & test suite dependencies
├── README.md                        # Project overview and runbooks
├── api/                             # FastAPI serving application
│   ├── Dockerfile                   # Python 3.11 container definition
│   ├── requirements.txt             # FastAPI, SQLAlchemy, Redis, Prometheus dependencies
│   └── app/
│       └── main.py                  # API routes: /health, /jobs, /stats, /metrics
├── scrapers/                        # Web crawler subsystem (Extract)
│   ├── Dockerfile                   # Scrapy runtime container
│   ├── requirements.txt             # Scrapy, BeautifulSoup4, MinIO, Redis dependencies
│   ├── scrapy.cfg                   # Scrapy deployment configuration
│   ├── settings.py                  # Scrapy settings: politeness, throttle, Dragonfly pipeline
│   ├── run.py                       # Resident producer process and stream initialization
│   ├── pipelines.py                 # DragonflyStreamPipeline (XADD to raw-jobs stream)
│   └── portals/                     # Spider adapters
│       ├── common.py                # Normalization utilities (IDs, salaries, HTML cleaning)
│       ├── example_spider.py        # Greenhouse ATS API adapter (GreenhouseSpider)
│       ├── ashby_spider.py          # Ashby ATS API adapter (AshbySpider)
│       ├── lever_spider.py          # Lever ATS API adapter (LeverSpider)
│       ├── workable_spider.py       # Workable API adapter (WorkableSpider)
│       ├── remoteok_spider.py       # RemoteOK public JSON API adapter
│       ├── remotive_spider.py       # Remotive public JSON API adapter
│       ├── weworkremotely_spider.py # We Work Remotely RSS/XML spider
│       ├── hn_spider.py             # Hacker News Firebase API spider
│       ├── himalayas_spider.py      # Himalayas job board spider
│       ├── aijobs_spider.py         # aijobs.net HTML spider
│       ├── arbeitnow_spider.py      # Arbeitnow API spider
│       ├── builtin_spider.py        # Built In HTML spider
│       ├── jobicy_spider.py         # Jobicy API spider
│       └── workingnomads_spider.py  # Working Nomads API spider
├── flows/                           # Prefect workflow orchestration (Transform & Load)
│   ├── scheduler.py                 # In-process prefect.serve scheduler daemon
│   ├── scrape_flow.py               # etl_flow: drains stream, transforms, loads multi-target
│   ├── scrape_portals.py            # scrape_portals_flow: fans out crawler execution
│   ├── seed_master_data.py          # seed_master_data_flow: populates dimension tables
│   ├── snapshot_analytics.py        # snapshot_analytics_flow: captures daily trend metrics
│   ├── mine_skills.py               # mine_skills_flow: unsupervised NLP skill candidate mining
│   ├── transform.py                 # Pure transformation logic: salary, seniority, skill matcher
│   └── dictionaries.py              # Lightweight YAML dictionary loaders and flatteners
├── data/                            # Domain master dictionaries
│   └── dictionaries/
│       ├── companies.yaml           # Company handles for ATS fan-out crawling
│       ├── job_portals.yaml         # Catalog of 25+ job portals and compliance profiles
│       ├── job_titles.yaml          # Canonical job titles, tracks, synonyms, and salary bands
│       ├── skills_technologies.yaml # Taxonomy of technical skills with aliases and weights
│       ├── roles_responsibilities.yaml # Responsibility regex patterns by area
│       └── search_keywords.yaml     # Boolean search queries and signals
├── db/                              # Database initialization & migrations
│   ├── init/
│   │   ├── 00_databases.sql         # Multi-database provisioning (prefect, metabase, jobs)
│   │   ├── 01_schema.sql            # Core jobs schema with pgvector extension & HNSW index
│   │   ├── 02_master_data.sql       # Companies, portals, skills, job_titles, portal_runs, views
│   │   ├── 03_analytics.sql         # Daily snapshot tables, skill_momentum, salary_benchmark
│   │   └── 04_skill_mining.sql      # Skill candidates table and new_skill_candidates view
│   └── seed/
│       └── sample_jobs.sql          # Seed dataset for local bootstrapping
├── monitoring/                      # Observability configurations
│   ├── prometheus.yml               # Scrape configurations for Prefect server & FastAPI
│   └── grafana/
│       ├── provisioning/            # Datasource configurations (Prometheus, PostgreSQL)
│       └── dashboards/              # JSON definitions for ETL Overview & Market Analytics
├── prefect/                         # Custom Prefect container assets
│   ├── Dockerfile                   # prefecthq/prefect:3.2.14-python3.12 image definition
│   └── requirements.txt             # Asyncpg, Elasticsearch, MinIO, Scrapy dependencies
├── scripts/                         # Automation & maintenance utilities
│   └── setup_metabase.py            # Automated Metabase API provisioning script (23 cards)
├── tests/                           # Unit test suite
│   ├── conftest.py                  # Pytest path bootstrapping and dictionary mock paths
│   ├── test_common.py               # Tests for spider normalization helpers
│   ├── test_dictionaries.py         # Tests for dictionary flatteners and PyYAML coercion
│   ├── test_spiders.py              # Tests for Scrapy normalization logic
│   └── test_transform.py            # Tests for enrichment, salary parsing, and NLP matching
├── notebooks/                       # Persistent directory for Jupyter/PySpark notebooks
└── docs/                            # Project specifications and guides
    ├── PLAN.md                      # High-level architecture and roadmaps
    ├── ARCHITECTURE.md              # C4 model architecture diagrams and notes
    ├── COMPLIANCE.md                # Legal, robots.txt, and ethical scraping guidelines
    ├── BACKLOG.md                   # Known issues, pending features, and ATS token fixes
    └── TEST_CASES.md                # Test matrix and coverage documentation
```

- **Component Interaction:**
  - **Scrapers $\rightarrow$ Dragonfly:** Scrapy pipelines serialize normalized Python dictionaries to JSON and execute Redis `XADD raw-jobs * data <json>`.
  - **Prefect Scheduler $\rightarrow$ Scrapers:** `flows/scrape_portals.py` executes headless Scrapy sub-processes using `subprocess.run(["scrapy", "crawl", spider, ...])`, parsing stdout/stderr to track emitted records.
  - **Prefect Consumer $\rightarrow$ Storage:** `flows/scrape_flow.py` reads from Dragonfly using `XREADGROUP` and `XAUTOCLAIM`, executes asynchronous SQL upserts via `asyncpg`, indexes JSON via the Elasticsearch HTTP client, and writes raw objects via the MinIO S3 SDK.
  - **FastAPI $\rightarrow$ Database:** FastAPI queries PostgreSQL directly via SQLAlchemy with connection pooling (`pool_pre_ping=True`) and reads stream queue backlog lengths directly from Dragonfly.
  - **Metabase $\rightarrow$ PostgreSQL:** Metabase connects to the `jobs` database on port 5432, executing analytical queries against tables (`jobs`, `companies`, `portal_runs`) and analytical SQL views (`skill_frequency`, `skill_cooccurrence`, `skill_momentum`, `salary_benchmark`).
  - **Prometheus $\rightarrow$ Services:** Prometheus scrapes `/api/metrics` on Prefect Server and `/metrics` on FastAPI every 15 seconds.

---

## 4. Workflows & Data Flow Execution

### 4.1 Primary Request/Event Lifecycle: Ingestion to Serving
1. **Trigger & Fan-out:** 
   - The Prefect scheduler triggers `scrape_portals_flow` on a scheduled cron (default `07:00 America/New_York`).
   - The flow reads `data/dictionaries/companies.yaml`, generating individual crawling tasks for standalone boards and per-company ATS handles (e.g., Ashby, Greenhouse, Lever, Workable).
2. **Extraction & Local Normalization (`scrapers/portals/`):**
   - The spider fetches API endpoints (or HTML pages).
   - Generates a deterministic primary key via SHA-256: `id = sha256(source:external_id)`.
   - Populates a canonical `base_record` with source metadata, raw description, URLs, and posting timestamps.
3. **Queue Ingestion (`scrapers/pipelines.py`):**
   - The Scrapy pipeline `DragonflyStreamPipeline` validates the item and issues an `XADD raw-jobs * data <json>` command to Dragonfly.
   - Crawl status and total job counts are logged to the `portal_runs` table in PostgreSQL.
4. **Stream Consumption & Batch Processing (`flows/scrape_flow.py`):**
   - The `etl_flow` runs on an interval (default every 30 minutes).
   - **Fault Recovery:** First invokes `xautoclaim(raw-jobs, jobs-ingest, consumer-1, min_idle_time=5000, count=100)` to reclaim messages that were abandoned by crashed consumers.
   - **Stream Consumption:** Issues `xreadgroup(jobs-ingest, consumer-1, {raw-jobs: ">"}, count=100, block=1000)`.
5. **Transformation & NLP Enrichment (`flows/transform.py`):**
   - **Salary Classification:** `compute_salary_ok()` parses `salary_min` and `salary_max`. If either is $\ge \$150,000$, sets `salary_ok = True`.
   - **Title Canonicalization:** `canonicalize_title()` matches title tokens against canonical titles in `data/dictionaries/job_titles.yaml` by choosing the longest matching synonym.
   - **Seniority Extraction:** `detect_seniority()` inspects title and description text using word-boundary regex matching against a hierarchical priority list (`c_level` down to `senior`, `lead`).
   - **Skill Extraction:** `extract_skills()` normalizes text and matches against categorized aliases from `skills_technologies.yaml`, emitting `[{name, category, weight}]`.
   - **Responsibility Extraction:** `extract_responsibilities()` detects functional phrases defined in `roles_responsibilities.yaml`.
6. **Multi-Target Persistence:**
   - **PostgreSQL:** Upserts the canonical record into `jobs` table using PostgreSQL `INSERT ... ON CONFLICT (id) DO UPDATE ...`, updating `last_seen_at` and description while preserving first discovery. Upserts company metadata into `companies`.
   - **Elasticsearch:** Indexes the transformed document into index `jobs` with keyword-optimized mappings for fast filtering.
   - **MinIO:** Archives raw JSON into bucket `raw-jobs` under the key `{source}/{id}.json`.
   - **Stream Acknowledgment:** Calls `xack(raw-jobs, jobs-ingest, message_id)`.
7. **Serving & Query Execution:**
   - End users or automated bots issue HTTP requests to FastAPI: `GET /jobs?min_salary=150000&remote=true&skill=pytorch`.
   - Query filters are dynamically constructed in SQL and executed against indexed PostgreSQL columns (`idx_jobs_salary`, `idx_jobs_remote`, `idx_jobs_posted`).

### 4.2 Secondary Scheduled Workflows
- **Master Data Seeding (`flows/seed_master_data.py`):** Runs daily at 06:30. Reads local YAML files, flattens hierarchies into relational tabular rows, and idempotently upserts `skills`, `portals`, `job_titles`, and `companies`.
- **Analytics Snapshots (`flows/snapshot_analytics.py`):** Runs daily at 08:30. Aggregates aggregate totals and categorical counts from `jobs`, inserting point-in-time rows into `analytics_snapshots`, `skill_trend`, `title_trend`, `company_hiring`, and `source_trend`.
- **Skill Mining (`flows/mine_skills.py`):** Runs daily at 09:00. Scans all active job descriptions, extracts n-gram technical phrases and camelCase/acronym tokens, filters out stopwords, known skills, and ATS slugs, and records candidates with $\ge 3$ occurrences into `skill_candidates`.

### 4.3 Authentication & Authorization
- **FastAPI Service:** Operating without authentication by default for internal/local development.
- **Database Access:** PostgreSQL credentials partitioned across functional databases (`postgres` superuser, `prefect` application role).
- **Elasticsearch:** Operating with `xpack.security.enabled=false` and `xpack.security.http.ssl.enabled=false` for dev convenience.
- **MinIO Lake:** Secured via access/secret key pairs (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`).
- **Grafana & Metabase:** Standard local credential-based administration (Metabase configured via API token setup; Grafana provisioned via environment variables).

### 4.4 Error Handling & Logging
- **Scraper Resiliency:** Spider runs are isolated in separate sub-processes within `scrape_portals_flow`. Failures in individual company boards (e.g., 404s on decommissioned ATS slugs) are caught, timed out after 1,200 seconds, and recorded in `portal_runs` with standard error logs without aborting the batch.
- **Message Acknowledgment Protocol:** Dragonfly messages are only acknowledged (`XACK`) once PostgreSQL upsert, Elasticsearch indexing, and MinIO archiving have completed successfully. Stuck messages are automatically recovered using `XAUTOCLAIM`.
- **FastAPI Fault Tolerance:** Database connection health checks (`GET /health`) run `SELECT 1` with `pool_pre_ping=True`, returning HTTP 503 if unreachable.
- **Structured Logging:** Standardized Python logging throughout `flows/` and `scrapers/`, combined with Prometheus gauges (`etl_stream_backlog`, `etl_stream_pending`, `etl_portal_runs_total`).

---

## 5. Getting Started & Development Setup

### 5.1 Prerequisites
- **Docker Engine:** Version 24.0+ with Docker Compose v2.
- **Python:** Python 3.11 or 3.12 (for local development, running tests, or manual scripts).
- **Make:** GNU Make utility.
- **Hardware Resources:** Recommended minimum 8 GB RAM and 4 CPU cores (Spark, Elasticsearch, and PostgreSQL run concurrently).

### 5.2 Local Setup Steps
```bash
# 1. Clone repository and navigate to root
cd d:\job_se

# 2. Configure environment variables from template
cp .env.example .env
# Note: On Windows PowerShell, use: Copy-Item .env.example .env

# 3. Spin up the entire Docker stack
make up
# Or: docker compose up -d

# 4. Verify that core containers are healthy
docker compose ps

# 5. Initialize Prefect database migrations (runs container job)
make init-prefect

# 6. Apply database schemas and analytical views
make migrate

# 7. Seed master data dimensions from YAML dictionaries
make seed-master

# 8. (Optional) Load sample data for immediate API exploration
make seed-db

# 9. (Optional) Provision Metabase dashboards and cards
docker compose exec -T prefect-scheduler python - < scripts/setup_metabase.py
```

### 5.3 Service Verification & Health Checks
| Component | Verification Command / URL | Expected Result |
|---|---|---|
| **FastAPI Health** | `curl http://localhost:8000/health` | `{"status":"ok","database":"ok"}` |
| **FastAPI Docs** | Open `http://localhost:8000/docs` in browser | Interactive Swagger UI |
| **Prefect Server** | Open `http://localhost:4200` | Prefect 3 dashboard showing deployments |
| **Elasticsearch** | `curl http://localhost:9200` | Cluster metadata, status green/yellow |
| **MinIO Console**| Open `http://localhost:9101` (user: minioadmin / pass: minioadmin) | Bucket `raw-jobs` visible |
| **Metabase** | Open `http://localhost:3101` (admin@example.com / admin12345) | "Job Search" dashboard |
| **Grafana** | Open `http://localhost:3100` (admin / admin) | ETL Overview and Market Analytics |

### 5.4 Testing & Verification
```bash
# 1. Create a local virtual environment and install test dependencies
make venv
# PowerShell alternative:
# python -m venv .venv
# .\.venv\Scripts\pip install -r requirements-dev.txt

# 2. Run unit tests across scrapers, dictionary loaders, and transforms
make test
# Direct command:
# .venv/bin/pytest tests/ -v
# Windows PowerShell direct command:
# .\.venv\Scripts\python -m pytest tests/ -v
```

---

## 6. Technical Debt & Risks

### 6.1 Known Bottlenecks & Critical Architectural Bugs
- **Duplicate Run Persistence in `flows/scrape_portals.py`:**
  In `scrape_portals_flow`, each spider result is persisted inside the execution loop (`await _persist_runs(engine, [result])` at line 131) and the entire results list is persisted *again* outside the loop (`await _persist_runs(engine, results)` at line 136). This doubles the run records in `portal_runs`, skewing freshness metrics and execution counts.
- **Synchronous Database Blocking in FastAPI (`api/app/main.py`):**
  FastAPI endpoint routes (`list_jobs`, `stats`, `metrics`) use synchronous SQLAlchemy `create_engine` with blocking calls (`conn.execute()`). Because these routes are declared as standard synchronous functions (`def`), Uvicorn runs them in a worker thread pool. However, if load increases or queries run slowly, thread pool exhaustion will degrade API throughput.
- **Unbounded Dragonfly Stream Growth:**
  The `raw-jobs` stream in Dragonfly uses `xadd(STREAM, {"data": ...})` without stream capping (`maxlen` or `MINID`). Because Dragonfly has a 512MB RAM cap (`--maxmemory=512mb`), long-running streams will eventually hit memory limits unless periodic `XTRIM` or eviction policies are enforced.
- **Missing Poison-Pill / Dead Letter Queue (DLQ):**
  In `flows/scrape_flow.py`, if a malformed JSON payload crashes `transform_record()` or violates SQL constraints, the transaction rolls back. Messages remain in `XPENDING` and are continuously re-claimed via `xautoclaim`, creating an infinite retry loop for unprocessable messages.
- **Spark Cluster Resource Idle State:**
  Spark Master and Worker containers are allocated in `docker-compose.yml` (consuming 2 CPU cores and 2GB RAM), yet current scheduled flows execute normalization purely inside Python Prefect flows. Spark is not currently integrated into the daily scheduled pipeline.

### 6.2 Missing or Incomplete Elements
- **Inactive Semantic Search / pgvector Embeddings:**
  The `jobs` table defines `embedding vector(1536)` and an HNSW index, but `flows/transform.py` does not generate embeddings (no vector embedding model or API integration). As a result, `api/app/main.py` falls back to `ILIKE` substring search for parameter `q`.
- **Stale ATS Handles in `companies.yaml`:**
  As logged in `docs/BACKLOG.md`, approximately 17 company handles in `data/dictionaries/companies.yaml` are broken or return 404s (e.g., Snowflake, DoorDash, Uber, Square, Shopify on Greenhouse; Vercel, Mistral on Ashby). Furthermore, the Lever spider (`api.lever.co/v0/postings/`) fails to retrieve postings due to endpoint deprecation.
- **Missing Cross-Source Deduplication:**
  Postings are keyed strictly on `sha256(source:external_id)`. If an employer posts a role on Greenhouse and it is mirrored across RemoteOK and We Work Remotely, three distinct records are stored with no cross-platform identity resolution.
- **Absence of CI/CD Pipeline:**
  The repository contains unit tests under `tests/`, but lacks automated GitHub Actions or GitLab CI workflows (`.github/workflows/`) to execute tests and linting on pull requests.

---

## 7. Future Recommendations & Roadmap

### 7.1 Architectural Improvements
- **Implement Dead-Letter Queue (DLQ) & Stream Trimming:**
  - Update `scrapers/pipelines.py` and `scrapers/run.py` to use approximate stream trimming: `xadd(STREAM, {"data": ...}, maxlen=100000, approximate=True)`.
  - Add error handling in `flows/scrape_flow.py` to catch `ValueError`/`KeyError` exceptions, send failed payloads to a `raw-jobs-dlq` stream, and acknowledge the original message to prevent infinite reprocessing loops.
- **Migrate FastAPI to Native Asynchronous SQLAlchemy:**
  - Transition `api/app/main.py` from `psycopg2-binary` and synchronous `create_engine` to `asyncpg` and `create_async_engine`, harmonizing database access patterns with `flows/` and eliminating thread pool contention.
- **Cross-Source Fuzzy Deduplication:**
  - Create a deduplication stage in the ETL pipeline using normalized company names and job titles: `fuzzy_id = sha256(norm_company:norm_title:location)`. Link duplicate postings to a primary job entity to prevent redundant search results and distorted analytics.

### 7.2 Feature Enhancements
- **Productionize Vector Embeddings Pipeline:**
  - Integrate an embedding generation step in `flows/transform.py` using a lightweight local embedding model (e.g., `sentence-transformers/all-MiniLM-L6-v2`) or OpenAI API (`text-embedding-3-small`).
  - Activate vector similarity querying in `api/app/main.py` using pgvector's cosine distance operator (`embedding <=> :query_vector`).
- **Lever Spider Modernization & ATS Token Audit:**
  - Update `lever_spider.py` to inspect newer Lever endpoints or fall back to company career page HTML parsing.
  - Audit and update tokens in `data/dictionaries/companies.yaml` to ensure healthy crawl yield.
- **Hacker News Algolia Auto-Discovery:**
  - Update `hn_spider.py` to automatically discover the current month's "Ask HN: Who is hiring?" item ID via the Algolia Search API (`hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring`), removing the requirement for manual `item_id` injection.
- **Spark Medallion Lakehouse Execution:**
  - Mount `hadoop-aws` and `aws-java-sdk-bundle` JARs into Spark workers to enable S3A access to MinIO.
  - Implement a daily PySpark batch job to aggregate raw JSON from MinIO into an optimized Delta/Parquet Gold analytical layer.

### 7.3 Security & Reliability Hardening
- **Authentication & API Rate Limiting:**
  - Implement API Key or JWT authentication on FastAPI endpoints.
  - Introduce token-bucket rate limiting via Dragonfly for public API routes.
- **Elasticsearch and Database Security Hardening:**
  - Enable basic authentication and TLS for Elasticsearch (`xpack.security.enabled=true`).
  - Remove default passwords (`postgres`, `prefect`, `minioadmin`, `admin12345`) in production deployment profiles.
- **Automated CI/CD:**
  - Add a GitHub Actions workflow (`.github/workflows/ci.yml`) to enforce automated test execution (`pytest`), linting (`flake8` or `ruff`), and Docker Compose validation (`docker compose config`) on every push.

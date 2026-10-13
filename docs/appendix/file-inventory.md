# Appendix — Exhaustive File Inventory & Asset Register

- **Last-Analyzed Commit**: `8ff63675b59f0f5c1cd3d4bdcb3f8d74229ef6a5`
- **Audience**: Developers, Auditors, Code Reviewers, Systems Integrators
- **Prerequisites**: Access to the repository workspace at `d:\job_se`

> [!NOTE]
> **Assumptions & Open Questions**
> - **Assumption**: Every file tracked by Git is audited and classified below according to its primary functional responsibility.

---

## Table of Contents
1. [Root & Operational Files](#1-root--operational-files)
2. [AI & RAG Subsystem (`ai/`)](#2-ai--rag-subsystem-ai)
3. [FastAPI Serving Subsystem (`api/`)](#3-fastapi-serving-subsystem-api)
4. [Configuration Subsystem (`config/`)](#4-configuration-subsystem-config)
5. [Core Domain Kernel (`core/`)](#5-core-domain-kernel-core)
6. [Data Dictionaries (`data/dictionaries/`)](#6-data-dictionaries-datadictionaries)
7. [Database Schemas (`db/`)](#7-database-schemas-db)
8. [Prefect Orchestration Flows (`flows/`)](#8-prefect-orchestration-flows-flows)
9. [Monitoring & Observability (`monitoring/`)](#9-monitoring--observability-monitoring)
10. [Scrapy Web Crawlers (`scrapers/`)](#10-scrapy-web-crawlers-scrapers)
11. [Operational Scripts (`scripts/`)](#11-operational-scripts-scripts)
12. [Test Suite (`tests/`)](#12-test-suite-tests)
13. [Change Log](#13-change-log)

---

## 1. Root & Operational Files

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `docker-compose.yml` | Master 12-service infrastructure topology specification. | **ACTIVE** |
| `Makefile` | Standard GNU Make task runner (up, down, migrate, seed, test). | **ACTIVE** |
| `run_all.bat` | Windows Master Pipeline runner with dual Docker/Local fallback detection. | **ACTIVE** |
| `pyproject.toml` | Build-system metadata, Ruff linter, Mypy typing, and Pytest configuration. | **ACTIVE** |
| `.env.example` | Template for environment variables and datastore credentials. | **CONFIG** |
| `requirements-dev.txt` | Pinned local developer and test execution dependencies. | **CONFIG** |
| `README.md` | Primary repository project overview and service URLs table. | **DOCS** |
| `IMPLEMENTATION.md` | Detailed architectural implementation blueprint and log. | **DOCS** |

---

## 2. AI & RAG Subsystem (`ai/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `ai/adapters/embeddings/openai_embedder.py` | OpenAI client generating 1536-dim dense vectors (`text-embedding-3-small`). | **ACTIVE** |
| `ai/adapters/embeddings/sentence_transformer.py` | Local sentence-transformer fallback embedder (`all-MiniLM-L6-v2`). | **ACTIVE** |
| `ai/adapters/llm/openai_adapter.py` | OpenAI GPT-4o client for structured extraction. | **ACTIVE** |
| `ai/adapters/llm/anthropic_adapter.py` | Anthropic Claude 3.5 Sonnet adapter for complex reasoning. | **ACTIVE** |
| `ai/adapters/llm/local_adapter.py` | Local Ollama/vLLM HTTP client for offline execution. | **ACTIVE** |
| `ai/adapters/rerankers/cross_encoder.py` | Second-stage cross-encoder re-ranking retrieved job documents. | **ACTIVE** |
| `ai/agents/job_enrichment_agent.py` | Autonomous multi-step job enrichment agent placeholder. | ⚠️ **STUB** |
| `ai/agents/state_graph.py` | Dataclass state definitions for LangGraph workflows. | ⚠️ **STUB** |
| `ai/guardrails/input_guard.py` | Prompt injection detection and PII redaction filter. | **ACTIVE** |
| `ai/guardrails/output_guard.py` | Schema compliance and output validation filter. | **ACTIVE** |
| `ai/rag/chunking/job_description_chunker.py` | Section-aware JD chunker (Responsibilities, Requirements). | **ACTIVE** |
| `ai/rag/embedders/pipeline.py` | Batched embedding generation pipeline coordinator. | **ACTIVE** |
| `ai/rag/retrievers/bm25_retriever.py` | Elasticsearch BM25 full-text lexical retriever. | **ACTIVE** |
| `ai/rag/retrievers/vector_retriever.py` | PostgreSQL pgvector dense cosine distance retriever. | **ACTIVE** |
| `ai/rag/retrievers/hybrid_retriever.py` | Reciprocal Rank Fusion ($k=60$) combining vector and BM25 scores. | **ACTIVE** |
| `ai/rag/vector_stores/pgvector_store.py` | pgvector store executing `match_jobs_by_vector` queries. | **ACTIVE** |
| `ai/rag/vector_stores/elasticsearch_store.py`| Elasticsearch index store executing lexical queries. | **ACTIVE** |

---

## 3. FastAPI Serving Subsystem (`api/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `api/Dockerfile` | Container specification for FastAPI Uvicorn service. | **ACTIVE** |
| `api/requirements.txt` | Direct dependencies for FastAPI and datastore drivers. | **CONFIG** |
| `api/app/main.py` | Master FastAPI application factory and Prometheus `/metrics` collector. | **ACTIVE** |
| `api/app/routers/health.py` | Container health probe (`GET /health`). | **ACTIVE** |
| `api/app/routers/jobs.py` | Filtered, paginated listing of $150K+ remote jobs (`GET /jobs`). | **ACTIVE** |
| `api/app/routers/search.py` | Hybrid dense-vector and BM25 search endpoint (`GET /search`). | **ACTIVE** |
| `api/app/routers/stats.py` | Aggregate market indicators and salary benchmarks (`GET /stats`). | **ACTIVE** |
| `api/app/dependencies/db.py` | Cached SQLAlchemy async engine and connection pool provider. | **ACTIVE** |
| `api/app/dependencies/cache.py` | Dragonfly Redis client provider. | **ACTIVE** |
| `api/app/dependencies/auth.py` | Bearer token authentication dependency. | ⚠️ **VULNERABLE STUB** |
| `api/app/schemas/job.py` | Pydantic response models for job items and market statistics. | **ACTIVE** |
| `api/app/schemas/search.py` | Pydantic response models for hybrid search items and RRF scores. | **ACTIVE** |

---

## 4. Configuration Subsystem (`config/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `config/settings.py` | Pydantic `BaseSettings` singleton with layered environment fallbacks. | **ACTIVE** |
| `config/feature_flags.yaml` | Feature toggles for vector search, guardrails, and LLM extraction. | **ACTIVE** |
| `config/model_configs/openai_gpt4o.yaml` | Parameter config for OpenAI GPT-4o. | **CONFIG** |
| `config/model_configs/anthropic_claude.yaml`| Parameter config for Anthropic Claude 3.5 Sonnet. | **CONFIG** |
| `config/model_configs/local_embedding.yaml` | Parameter config for local SentenceTransformer model. | **CONFIG** |

---

## 5. Core Domain Kernel (`core/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `core/domain/job.py` | Canonical domain entity representing a validated job posting. | **ACTIVE** |
| `core/domain/salary.py` | Value object and domain logic enforcing `$150K+` threshold. | **ACTIVE** |
| `core/domain/skill.py` | Domain model for extracted skills and categorized taxonomies. | **ACTIVE** |
| `core/domain/company.py` | Domain model representing hiring organizations. | **ACTIVE** |
| `core/ports/llm_provider.py` | Protocol interface for Large Language Model backends. | **ACTIVE** |
| `core/ports/embedding_provider.py` | Protocol interface for text embedding providers. | **ACTIVE** |
| `core/ports/vector_store.py` | Protocol interface for vector databases and similarity search. | **ACTIVE** |
| `core/ports/reranker.py` | Protocol interface for cross-encoder rerankers. | **ACTIVE** |
| `core/ports/cache.py` | Protocol interface for in-memory caching and streams. | **ACTIVE** |
| `core/services/title_canonicalizer.py` | Standardizes raw job titles against standardized taxonomies. | **ACTIVE** |
| `core/services/seniority_detector.py` | Word-boundary regex detector for career seniority levels. | **ACTIVE** |
| `core/services/skill_extractor.py` | High-precision dictionary matcher for technical skills. | **ACTIVE** |
| `core/services/responsibility_extractor.py` | Functional role scope phrase extractor. | **ACTIVE** |

---

## 6. Data Dictionaries (`data/dictionaries/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `data/dictionaries/job_titles.yaml` | Taxonomy of canonical job titles and synonyms. | **ACTIVE** |
| `data/dictionaries/skills_technologies.yaml`| Taxonomy of technical skills, categories, weights, and aliases. | **ACTIVE** |
| `data/dictionaries/companies.yaml` | Catalog of target hiring companies and ATS tokens (Greenhouse, Lever). | **ACTIVE** |
| `data/dictionaries/job_portals.yaml` | Catalog of job boards, scraping methods, and priorities. | **ACTIVE** |
| `data/dictionaries/roles_responsibilities.yaml`| Catalog of functional responsibility phrases. | **ACTIVE** |
| `data/dictionaries/search_keywords.yaml` | Search keyword groups for query expansion. | **ACTIVE** |

---

## 7. Database Schemas (`db/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `db/init/00_databases.sql` | Role and database provisioning (`prefect`, `metabase`, `jobs`). | **ACTIVE** |
| `db/init/01_schema.sql` | Canonical `jobs` table and pgvector extension initialization. | **ACTIVE** |
| `db/init/02_master_data.sql` | Dimension tables (`companies`, `portals`, `skills`, `portal_runs`) and views. | **ACTIVE** |
| `db/init/03_analytics.sql` | Trend tables (`skill_trend`, `title_trend`) and `salary_benchmark` views. | **ACTIVE** |
| `db/init/04_skill_mining.sql` | Mined `skill_candidates` table and promotion view. | **ACTIVE** |
| `db/init/05_embeddings.sql` | HNSW cosine vector index and `match_jobs_by_vector` procedure. | **ACTIVE** |
| `db/seed/sample_jobs.sql` | Synthetic sample job postings for offline development. | **ACTIVE** |

---

## 8. Prefect Orchestration Flows (`flows/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `flows/scheduler.py` | In-process Prefect 3 scheduler serving 5 deployments. | **ACTIVE** |
| `flows/scrape_portals.py` | Daily flow executing 14 Scrapy spiders; writes `portal_runs`. | **ACTIVE** |
| `flows/scrape_flow.py` | Core ETL: drains Redis Stream, transforms, loads Postgres, ES, MinIO. | **ACTIVE** |
| `flows/seed_master_data.py` | Daily dimension sync from YAML files into PostgreSQL. | **ACTIVE** |
| `flows/mine_skills.py` | Daily skill mining flow populating `skill_candidates`. | **ACTIVE** |
| `flows/snapshot_analytics.py` | Daily snapshot flow writing to `analytics_snapshots`. | **ACTIVE** |
| `flows/embed_jobs_flow.py` | Batch flow generating vector embeddings for unembedded jobs. | **ACTIVE** |
| `flows/dlq_handler.py` | Dead-Letter Queue manager routing poisoned messages and replay. | **ACTIVE** |
| `flows/transform.py` | Single coordinator applying domain services to a raw record. | **ACTIVE** |
| `flows/dictionaries.py` | Dependency-light flattening logic for YAML dictionaries. | **ACTIVE** |

---

## 9. Monitoring & Observability (`monitoring/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `monitoring/prometheus.yml` | Prometheus 15s scrape interval config for FastAPI and Prefect. | **ACTIVE** |
| `monitoring/grafana/dashboards/etl-overview.json` | Provisioned Grafana dashboard for stream depth and spider telemetry. | **ACTIVE** |
| `monitoring/grafana/dashboards/market-analytics.json`| Provisioned Grafana dashboard for market trends. | **ACTIVE** |

---

## 10. Scrapy Web Crawlers (`scrapers/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `scrapers/Dockerfile` | Container spec for crawler runtime. | **ACTIVE** |
| `scrapers/settings.py` | Scrapy settings, AutoThrottle politeness, and pipeline registration. | **ACTIVE** |
| `scrapers/pipelines.py` | `DragonflyStreamPipeline` pushing scraped items to Redis Stream. | **ACTIVE** |
| `scrapers/run.py` | Resident daemon script ensuring stream existence. | ⚠️ **TECH DEBT / SLEEP LOOP** |
| `scrapers/portals/common.py` | Ingestion normalization primitives (regex, stable hashing). | **ACTIVE** |
| `scrapers/portals/example_spider.py` | Active Greenhouse ATS spider via JSON API. | ⚠️ **MISNAMED FILE** |
| `scrapers/portals/lever_spider.py` | Lever ATS spider via JSON API. | **ACTIVE** |
| `scrapers/portals/ashby_spider.py` | Ashby ATS spider via public API. | **ACTIVE** |
| `scrapers/portals/workable_spider.py` | Workable ATS spider. | **ACTIVE** |
| `scrapers/portals/remoteok_spider.py` | RemoteOK job board spider. | **ACTIVE** |
| `scrapers/portals/remotive_spider.py` | Remotive job board spider. | **ACTIVE** |
| `scrapers/portals/weworkremotely_spider.py`| We Work Remotely job board spider. | **ACTIVE** |
| `scrapers/portals/arbeitnow_spider.py` | Arbeitnow job board spider. | **ACTIVE** |
| `scrapers/portals/himalayas_spider.py` | Himalayas job board spider. | **ACTIVE** |
| `scrapers/portals/jobicy_spider.py` | Jobicy job board spider. | **ACTIVE** |
| `scrapers/portals/workingnomads_spider.py`| Working Nomads job board spider. | **ACTIVE** |
| `scrapers/portals/aijobs_spider.py` | AIJobs.net spider. | **ACTIVE** |
| `scrapers/portals/builtin_spider.py` | BuiltIn tech job board spider. | **ACTIVE** |
| `scrapers/portals/hn_spider.py` | Hacker News "Who is Hiring?" thread spider. | **ACTIVE** |

---

## 11. Operational Scripts (`scripts/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `scripts/run_real_pipeline_local.py` | Direct synchronous live ETL runner bypassing Docker. | **ACTIVE** |
| `scripts/verify_all_pipelines.py` | Comprehensive end-to-end integration test harness. | **ACTIVE** |
| `scripts/setup_metabase.py` | Automated REST provisioning of Metabase cards and dashboards. | **ACTIVE** |
| `scripts/backfill_embeddings.py` | Batch vector embedding backfiller for pgvector. | **ACTIVE** |
| `scripts/evaluate_prompts.py` | GenAI evaluation gate for regression testing Jinja prompt templates. | **ACTIVE** |

---

## 12. Test Suite (`tests/`)

| File Path | Functional Responsibility | Status |
| :--- | :--- | :--- |
| `tests/conftest.py` | Pytest fixtures and mock configurations. | **TEST** |
| `tests/test_common.py` | Unit tests for `scrapers/portals/common.py` primitives. | **TEST** |
| `tests/test_dictionaries.py` | Unit tests for `flows/dictionaries.py` flattening logic. | **TEST** |
| `tests/test_spiders.py` | Parsing tests for Scrapy spider adapters. | **TEST** |
| `tests/test_transform.py` | Unit tests for `flows/transform.py::transform_record()`. | **TEST** |
| `tests/unit/core/test_salary.py` | Unit tests for `$150K+` compensation validation. | **TEST** |
| `tests/unit/core/test_skill_extractor.py` | Unit tests for technical skill extractor. | **TEST** |
| `tests/unit/core/test_title_canonicalizer.py`| Unit tests for canonical title matching. | **TEST** |
| `tests/unit/ai/test_llm_adapters.py` | Unit tests for OpenAI, Anthropic, and Local LLM adapters. | **TEST** |
| `tests/unit/ai/test_retrievers.py` | Unit tests for Vector, BM25, and Hybrid RRF retrievers. | **TEST** |
| `tests/unit/rag/test_chunking.py` | Unit tests for semantic job description chunker. | **TEST** |
| `tests/integration/test_etl_pipeline.py` | End-to-end integration test for stream consumption and loading. | **TEST** |

---

## 13. Change Log

| Version | Date | Author | Description of Changes |
| :--- | :--- | :--- | :--- |
| `1.0.0` | 2026-10-13 | Architecture Team | Exhaustive file-by-file audit and inventory covering all 80+ codebase assets. |

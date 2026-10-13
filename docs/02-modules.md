# 02 — Module Decomposition & Layer Catalog

- **Last-Analyzed Commit**: `8ff63675b59f0f5c1cd3d4bdcb3f8d74229ef6a5`
- **Audience**: Backend Engineers, Data Engineers, AI Engineers
- **Prerequisites**: Working knowledge of Python typing, Clean Architecture ports & adapters, and Scrapy/FastAPI internals

> [!NOTE]
> **Assumptions & Open Questions**
> - **Assumption**: Modules in `core/` remain strictly pure Python with zero database or web framework dependencies.
> - **Open Question**: When will `ai/agents/job_enrichment_agent.py` be upgraded from a stub to a full LangGraph multi-agent workflow?

---

## Table of Contents
1. [Decomposition Overview](#1-decomposition-overview)
2. [Ingestion Layer](#2-ingestion-layer)
3. [Transform & Domain Kernel Layer](#3-transform--domain-kernel-layer)
4. [AI / GenAI & RAG Layer](#4-ai--genai--rag-layer)
5. [Orchestration Layer](#5-orchestration-layer)
6. [Storage Layer](#6-storage-layer)
7. [Serving Layer](#7-serving-layer)
8. [Observability & Analytics Layer](#8-observability--analytics-layer)
9. [Auth & Security Layer](#9-auth--security-layer)
10. [Change Log](#10-change-log)

---

## 1. Decomposition Overview

The codebase is partitioned into nine distinct architectural layers adhering strictly to Clean Architecture boundaries:

```
[ Ingestion ] ──> [ Stream Buffer ] ──> [ Orchestration ] ──> [ Transform Kernel ]
                                                                      │
[ Serving ] <── [ Storage (Postgres, ES, S3) ] <──────────────────────┘
      ▲                       ▲
      │                       │
[ AI / RAG Layer ]    [ Observability ]
```

---

## 2. Ingestion Layer

### Layer Inventory
| Module | Path | Responsibility | Status | Test File |
| :--- | :--- | :--- | :--- | :--- |
| `scrapers.portals.common` | [scrapers/portals/common.py](file:///d:/job_se/scrapers/portals/common.py) | Ingestion primitives (salary regex, remote detector, stable ID). | **ACTIVE** | [tests/test_common.py](file:///d:/job_se/tests/test_common.py) |
| `scrapers.pipelines` | [scrapers/pipelines.py](file:///d:/job_se/scrapers/pipelines.py) | Scrapy pipeline pushing scraped items to Dragonfly Redis Streams. | **ACTIVE** | [tests/test_spiders.py](file:///d:/job_se/tests/test_spiders.py) |
| `scrapers.settings` | [scrapers/settings.py](file:///d:/job_se/scrapers/settings.py) | Scrapy engine configuration, AutoThrottle politeness middleware. | **ACTIVE** | Configuration |
| `scrapers.run` | [scrapers/run.py](file:///d:/job_se/scrapers/run.py) | Resident daemon script holding container open. | ⚠️ **DEAD/STUB** | Manual |
| Standalone Spiders (9 Spiders) | `scrapers/portals/*_spider.py` | Standalone remote job crawlers (RemoteOK, Remotive, WWR, etc.). | **ACTIVE** | [tests/test_spiders.py](file:///d:/job_se/tests/test_spiders.py) |
| ATS Spiders (4 Spiders) | `scrapers/portals/*_spider.py` | Company ATS crawlers (Greenhouse, Lever, Ashby, Workable). | **ACTIVE** | [tests/test_spiders.py](file:///d:/job_se/tests/test_spiders.py) |

### Detailed Module Breakdown

#### `scrapers.portals.common`
- **Path**: [scrapers/portals/common.py](file:///d:/job_se/scrapers/portals/common.py)
- **Responsibility**: Provides normalization primitives, regex cleaners, deterministic ID generation, and base schema initialization.
- **Public Interface**:
  - `stable_id(source: str, external_id: str, company: str = "") -> str` ([L27](file:///d:/job_se/scrapers/portals/common.py#L27)): Returns SHA256 hex digest.
  - `strip_html(text: str) -> str` ([L36](file:///d:/job_se/scrapers/portals/common.py#L36)): Strips HTML tags and unescapes entities.
  - `extract_salary(text: str) -> tuple[float | None, float | None]` ([L44](file:///d:/job_se/scrapers/portals/common.py#L44)): Extracts salary bounds.
  - `is_remote_text(*texts: str) -> bool` ([L68](file:///d:/job_se/scrapers/portals/common.py#L68)): Word-boundary regex detector for remote terms.
  - `base_record(...) -> dict[str, Any]` ([L90](file:///d:/job_se/scrapers/portals/common.py#L90)): Initializes canonical job payload dictionary.
- **Inputs / Outputs**: Raw HTML strings $\rightarrow$ Standardized primitives and canonical dictionary.
- **Dependencies**: Standard library (`re`, `hashlib`, `html`). Zero external dependencies.
- **Side Effects**: None (Pure CPU computation).

#### `scrapers.pipelines.DragonflyStreamPipeline`
- **Path**: [scrapers/pipelines.py:L21](file:///d:/job_se/scrapers/pipelines.py#L21)
- **Responsibility**: Scrapy Item Pipeline pushing scraped records into Dragonfly Stream `raw-jobs`.
- **Public Interface**: `open_spider(spider)`, `close_spider(spider)`, `process_item(item, spider)`.
- **Inputs / Outputs**: Scrapy item $\rightarrow$ Emitted Redis Stream message ID.
- **Side Effects**: Network socket write pushing JSON messages to Dragonfly; stream trimming (`maxlen=100000`).

---

## 3. Transform & Domain Kernel Layer

### Layer Inventory
| Module | Path | Responsibility | Status | Test File |
| :--- | :--- | :--- | :--- | :--- |
| `core.domain.job` | [core/domain/job.py](file:///d:/job_se/core/domain/job.py) | Canonical domain entity representing a validated job posting. | **ACTIVE** | Integration tests |
| `core.domain.salary` | [core/domain/salary.py](file:///d:/job_se/core/domain/salary.py) | Domain model and threshold validation for $150K compensation. | **ACTIVE** | [tests/unit/core/test_salary.py](file:///d:/job_se/tests/unit/core/test_salary.py) |
| `core.domain.skill` | [core/domain/skill.py](file:///d:/job_se/core/domain/skill.py) | Domain entity for extracted skills and categorized taxonomies. | **ACTIVE** | Unit tests |
| `core.domain.company` | [core/domain/company.py](file:///d:/job_se/core/domain/company.py) | Domain entity representing hiring organizations. | **ACTIVE** | Integration tests |
| `core.services.title_canonicalizer` | [core/services/title_canonicalizer.py](file:///d:/job_se/core/services/title_canonicalizer.py) | Standardizes raw titles against job title taxonomy. | **ACTIVE** | [tests/unit/core/test_title_canonicalizer.py](file:///d:/job_se/tests/unit/core/test_title_canonicalizer.py) |
| `core.services.seniority_detector` | [core/services/seniority_detector.py](file:///d:/job_se/core/services/seniority_detector.py) | Detects career level (c_level down to lead) using regex. | **ACTIVE** | [tests/test_transform.py](file:///d:/job_se/tests/test_transform.py) |
| `core.services.skill_extractor` | [core/services/skill_extractor.py](file:///d:/job_se/core/services/skill_extractor.py) | Extracts categorized technical skills and weights. | **ACTIVE** | [tests/unit/core/test_skill_extractor.py](file:///d:/job_se/tests/unit/core/test_skill_extractor.py) |
| `core.services.responsibility_extractor` | [core/services/responsibility_extractor.py](file:///d:/job_se/core/services/responsibility_extractor.py) | Extracts functional role scope phrases from descriptions. | **ACTIVE** | [tests/test_transform.py](file:///d:/job_se/tests/test_transform.py) |
| `flows.transform` | [flows/transform.py](file:///d:/job_se/flows/transform.py) | Single coordinator enriching a raw record with domain logic. | **ACTIVE** | [tests/test_transform.py](file:///d:/job_se/tests/test_transform.py) |
| `flows.dictionaries` | [flows/dictionaries.py](file:///d:/job_se/flows/dictionaries.py) | Flattens YAML taxonomy dictionaries for DB seeding. | **ACTIVE** | [tests/test_dictionaries.py](file:///d:/job_se/tests/test_dictionaries.py) |

#### `core.domain.salary`
- **Path**: [core/domain/salary.py](file:///d:/job_se/core/domain/salary.py)
- **Responsibility**: Pure domain compensation validator enforcing `SALARY_THRESHOLD = 150_000.0` ([L7](file:///d:/job_se/core/domain/salary.py#L7)).
- **Public Interface**:
  - `compute_salary_ok(record: dict[str, Any]) -> bool` ([L20](file:///d:/job_se/core/domain/salary.py#L20)): Returns `True` if `salary_min >= 150000` OR `salary_max >= 150000`. Returns `False` when salary is unknown or below threshold.
  - `Salary` frozen dataclass ([L31](file:///d:/job_se/core/domain/salary.py#L31)): Encapsulates min, max, currency, raw string, and `is_above_threshold` property.

---

## 4. AI / GenAI & RAG Layer

### Layer Inventory
| Module | Path | Responsibility | Status | Test File |
| :--- | :--- | :--- | :--- | :--- |
| `ai.adapters.embeddings.openai_embedder` | [ai/adapters/embeddings/openai_embedder.py](file:///d:/job_se/ai/adapters/embeddings/openai_embedder.py) | Generates 1536-dim vectors via `text-embedding-3-small`. | **ACTIVE** | [tests/unit/ai/test_retrievers.py](file:///d:/job_se/tests/unit/ai/test_retrievers.py) |
| `ai.adapters.embeddings.sentence_transformer` | [ai/adapters/embeddings/sentence_transformer.py](file:///d:/job_se/ai/adapters/embeddings/sentence_transformer.py) | Local fallback embedder via `all-MiniLM-L6-v2` (384-dim). | **ACTIVE** | Mocked |
| `ai.adapters.llm.openai_adapter` | [ai/adapters/llm/openai_adapter.py](file:///d:/job_se/ai/adapters/llm/openai_adapter.py) | OpenAI GPT-4o adapter for structured extraction. | **ACTIVE** | [tests/unit/ai/test_llm_adapters.py](file:///d:/job_se/tests/unit/ai/test_llm_adapters.py) |
| `ai.adapters.llm.anthropic_adapter` | [ai/adapters/llm/anthropic_adapter.py](file:///d:/job_se/ai/adapters/llm/anthropic_adapter.py) | Anthropic Claude 3.5 Sonnet adapter for complex reasoning. | **ACTIVE** | [tests/unit/ai/test_llm_adapters.py](file:///d:/job_se/tests/unit/ai/test_llm_adapters.py) |
| `ai.adapters.llm.local_adapter` | [ai/adapters/llm/local_adapter.py](file:///d:/job_se/ai/adapters/llm/local_adapter.py) | Local Ollama/vLLM HTTP adapter for offline execution. | **ACTIVE** | [tests/unit/ai/test_llm_adapters.py](file:///d:/job_se/tests/unit/ai/test_llm_adapters.py) |
| `ai.adapters.rerankers.cross_encoder` | [ai/adapters/rerankers/cross_encoder.py](file:///d:/job_se/ai/adapters/rerankers/cross_encoder.py) | Second-stage cross-encoder re-ranking retrieved jobs. | **ACTIVE** | Unit tests |
| `ai.rag.chunking.job_description_chunker` | [ai/rag/chunking/job_description_chunker.py](file:///d:/job_se/ai/rag/chunking/job_description_chunker.py) | Splits JDs into semantic sections (Requirements, Benefits). | **ACTIVE** | [tests/unit/rag/test_chunking.py](file:///d:/job_se/tests/unit/rag/test_chunking.py) |
| `ai.rag.retrievers.hybrid_retriever` | [ai/rag/retrievers/hybrid_retriever.py](file:///d:/job_se/ai/rag/retrievers/hybrid_retriever.py) | Fuses dense vector scores and BM25 scores via RRF ($k=60$). | **ACTIVE** | [tests/unit/ai/test_retrievers.py](file:///d:/job_se/tests/unit/ai/test_retrievers.py) |
| `ai.rag.vector_stores.pgvector_store` | [ai/rag/vector_stores/pgvector_store.py](file:///d:/job_se/ai/rag/vector_stores/pgvector_store.py) | Async pgvector store executing cosine distance queries. | **ACTIVE** | Integration tests |
| `ai.rag.vector_stores.elasticsearch_store`| [ai/rag/vector_stores/elasticsearch_store.py](file:///d:/job_se/ai/rag/vector_stores/elasticsearch_store.py) | Elasticsearch BM25 full-text index query provider. | **ACTIVE** | Integration tests |
| `ai.guardrails.input_guard` | [ai/guardrails/input_guard.py](file:///d:/job_se/ai/guardrails/input_guard.py) | Prompt injection defense and PII redaction filter. | **ACTIVE** | Guardrail tests |
| `ai.agents.job_enrichment_agent` | [ai/agents/job_enrichment_agent.py](file:///d:/job_se/ai/agents/job_enrichment_agent.py) | Autonomous multi-step enrichment agent placeholder. | ⚠️ **STUB** | None |
| `ai.agents.state_graph` | [ai/agents/state_graph.py](file:///d:/job_se/ai/agents/state_graph.py) | State schema for LangGraph agent workflows. | ⚠️ **STUB** | None |

---

## 5. Orchestration Layer

### Layer Inventory
| Module | Path | Responsibility | Status | Test File |
| :--- | :--- | :--- | :--- | :--- |
| `flows.scheduler` | [flows/scheduler.py](file:///d:/job_se/flows/scheduler.py) | Serves 5 scheduled deployments in-process via Prefect 3. | **ACTIVE** | Manual |
| `flows.scrape_portals` | [flows/scrape_portals.py](file:///d:/job_se/flows/scrape_portals.py) | Runs spider tasks and writes telemetry to `portal_runs`. | **ACTIVE** | [tests/test_spiders.py](file:///d:/job_se/tests/test_spiders.py) |
| `flows.scrape_flow` | [flows/scrape_flow.py](file:///d:/job_se/flows/scrape_flow.py) | Core ETL: drains Redis Stream, enriches, and loads datastores. | **ACTIVE** | [tests/integration/test_etl_pipeline.py](file:///d:/job_se/tests/integration/test_etl_pipeline.py) |
| `flows.seed_master_data`| [flows/seed_master_data.py](file:///d:/job_se/flows/seed_master_data.py) | Daily sync populating dimensions from YAML dictionaries. | **ACTIVE** | Integration tests |
| `flows.mine_skills` | [flows/mine_skills.py](file:///d:/job_se/flows/mine_skills.py) | Discovers candidate skills from job descriptions. | **ACTIVE** | Integration tests |
| `flows.snapshot_analytics`| [flows/snapshot_analytics.py](file:///d:/job_se/flows/snapshot_analytics.py) | Writes daily analytics snapshots to `analytics_snapshots`. | **ACTIVE** | Integration tests |
| `flows.embed_jobs_flow` | [flows/embed_jobs_flow.py](file:///d:/job_se/flows/embed_jobs_flow.py) | Batch vectorizer generating embeddings for unembedded jobs. | **ACTIVE** | Unit tests |
| `flows.dlq_handler` | [flows/dlq_handler.py](file:///d:/job_se/flows/dlq_handler.py) | Dead-Letter Queue manager isolating poisoned payloads. | **ACTIVE** | Integration tests |

---

## 6. Storage Layer

- **PostgreSQL 16 + pgvector**:
  - DDL Scripts: [db/init/00_databases.sql](file:///d:/job_se/db/init/00_databases.sql) through [05_embeddings.sql](file:///d:/job_se/db/init/05_embeddings.sql).
  - Primary Tables: `jobs`, `companies`, `portals`, `skills`, `job_titles`, `portal_runs`, `analytics_snapshots`, `skill_trend`, `title_trend`, `company_hiring`, `skill_candidates`.
  - HNSW Index: `idx_jobs_embedding_hnsw` on `jobs (embedding vector_cosine_ops)` with `m=16, ef_construction=64`.
- **Dragonfly v2.0**:
  - Streams: `raw-jobs` (primary inbound buffer) and `raw-jobs-dlq` (dead-letter queue).
  - Consumer Group: `jobs-ingest`.
- **Elasticsearch 8.13**:
  - Index: `jobs` containing keyword and text mappings for BM25 retrieval.
- **MinIO S3**:
  - Bucket: `raw-jobs` storing immutable JSON objects partitioned as `raw/{source}/{id}.json`.

---

## 7. Serving Layer

### Layer Inventory
| Module | Path | Responsibility | Status |
| :--- | :--- | :--- | :--- |
| `api.app.main` | [api/app/main.py](file:///d:/job_se/api/app/main.py) | FastAPI app factory and Prometheus `/metrics` collector. | **ACTIVE** |
| `api.app.routers.health` | [api/app/routers/health.py](file:///d:/job_se/api/app/routers/health.py) | Liveness and DB probe (`GET /health`). | **ACTIVE** |
| `api.app.routers.jobs` | [api/app/routers/jobs.py](file:///d:/job_se/api/app/routers/jobs.py) | Filtered, paginated job listing (`GET /jobs`). | **ACTIVE** |
| `api.app.routers.search` | [api/app/routers/search.py](file:///d:/job_se/api/app/routers/search.py) | Hybrid dense vector and BM25 search (`GET /search`). | **ACTIVE** |
| `api.app.routers.stats` | [api/app/routers/stats.py](file:///d:/job_se/api/app/routers/stats.py) | Market indicators and salary stats (`GET /stats`). | **ACTIVE** |
| `api.app.dependencies.db` | [api/app/dependencies/db.py](file:///d:/job_se/api/app/dependencies/db.py) | Cached async SQLAlchemy engine provider. | **ACTIVE** |
| `api.app.dependencies.cache`| [api/app/dependencies/cache.py](file:///d:/job_se/api/app/dependencies/cache.py) | Redis connection provider for Dragonfly. | **ACTIVE** |

---

## 8. Observability & Analytics Layer

- **Prometheus Scrape Endpoint**: `api/app/main.py:metrics()` ([api/app/main.py:L44](file:///d:/job_se/api/app/main.py#L44)). Exposes gauges for stream backlog, DLQ depth, company count, and spider run statuses.
- **Grafana Dashboards**: [monitoring/grafana/dashboards/etl-overview.json](file:///d:/job_se/monitoring/grafana/dashboards/etl-overview.json) and `market-analytics.json`.
- **Metabase Setup**: [scripts/setup_metabase.py](file:///d:/job_se/scripts/setup_metabase.py) automated provisioning script.

---

## 9. Auth & Security Layer

- **`api.app.dependencies.auth`**: [api/app/dependencies/auth.py](file:///d:/job_se/api/app/dependencies/auth.py).
  - Status: ⚠️ **SECURITY VULNERABILITY**: Does not verify cryptographic signatures (`token.startswith("eyJ")`). Not wired into any router.
- **`ai.guardrails`**: [ai/guardrails/input_guard.py](file:///d:/job_se/ai/guardrails/input_guard.py) and policies.
  - Status: **ACTIVE**: Enforces prompt injection defense and PII masking.

---

## 10. Change Log

| Version | Date | Author | Description of Changes |
| :--- | :--- | :--- | :--- |
| `1.0.0` | 2026-10-13 | Architecture Team | Complete layer-by-layer module catalog with exact line citations and interface specs. |

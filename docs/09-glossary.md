# 09 — Domain & Technical Glossary

- **Last-Analyzed Commit**: `8ff63675b59f0f5c1cd3d4bdcb3f8d74229ef6a5`
- **Audience**: All Audiences (Developers, Data Engineers, Ops, Candidates, Product Managers)
- **Prerequisites**: None

> [!NOTE]
> **Assumptions & Open Questions**
> - **Assumption**: Acronyms and technical terms adhere strictly to their concrete implementations within this repository.

---

## Table of Contents
1. [Core Domain Concepts](#1-core-domain-concepts)
2. [Data Engineering & Streaming Terms](#2-data-engineering--streaming-terms)
3. [GenAI, Search & Vector Terms](#3-genai-search--vector-terms)
4. [Acronyms & Abbreviations Matrix](#4-acronyms--abbreviations-matrix)
5. [Change Log](#5-change-log)

---

## 1. Core Domain Concepts

### Applicant Tracking System (ATS)
Software platforms (Greenhouse, Lever, Ashby, Workable) utilized by companies to manage recruiting workflows. In this platform, spiders fan out over company ATS boards registered in [data/dictionaries/companies.yaml](file:///d:/job_se/data/dictionaries/companies.yaml).

### Base Salary vs. Total Compensation (`base_vs_tc`)
A domain metadata classification indicating whether compensation represents guaranteed annual base salary (`base`), annualized full packages including equity/bonus (`total_comp`), or indeterminate structures (`unknown`).

### Canonical Job Schema
The unified, normalized domain contract implemented in [core/domain/job.py](file:///d:/job_se/core/domain/job.py). Represents a standardized job posting across disparate web sources with verified salary ranges and extracted skills.

### `salary_ok`
A strict boolean domain flag computed by `compute_salary_ok()` ([core/domain/salary.py:L20](file:///d:/job_se/core/domain/salary.py#L20)). Evaluates to `True` if and only if `salary_min >= 150000` OR `salary_max >= 150000` USD. Evaluates to `False` if salary is unspecified.

### Title Canonicalization
The process performed by `core/services/title_canonicalizer.py` ([core/services/title_canonicalizer.py:L32](file:///d:/job_se/core/services/title_canonicalizer.py#L32)) matching noisy job titles (e.g. "Lead Deep Learning Engineer") to standardized taxonomy titles (e.g. "Machine Learning Engineer").

---

## 2. Data Engineering & Streaming Terms

### AutoThrottle
An extension within Scrapy ([scrapers/settings.py:L19](file:///d:/job_se/scrapers/settings.py#L19)) that dynamically adjusts download latencies based on target server load and network round-trip time, preventing target server overload.

### Dead-Letter Queue (DLQ)
An isolated stream buffer (`raw-jobs-dlq`) managed by [flows/dlq_handler.py](file:///d:/job_se/flows/dlq_handler.py). Malformed, unparseable, or poisoned payloads are routed here to prevent blocking primary stream consumption.

### Dragonfly
A modern, ultra-high-throughput, multi-threaded drop-in replacement for Redis. Deployed in this platform ([docker-compose.yml:L84](file:///d:/job_se/docker-compose.yml#L84)) to power Redis Streams (`raw-jobs`) and consumer groups (`jobs-ingest`), replacing heavy Kafka dependencies.

### Redis Streams (`raw-jobs`)
An append-only log data structure in Dragonfly. Scrapy spiders emit records using `XADD`; Prefect ETL flows consume batches using `XREADGROUP` and commit offsets using `XACK`.

### `xautoclaim`
A Redis Streams primitive used in `flows/scrape_flow.py` ([flows/scrape_flow.py:L273](file:///d:/job_se/flows/scrape_flow.py#L273)) to automatically reclaim and reprocess pending messages left unacknowledged by crashed consumer instances.

---

## 3. GenAI, Search & Vector Terms

### BM25 Lexical Retrieval
Best Matching 25; a probabilistic ranking function utilized by Elasticsearch ([docker-compose.yml:L58](file:///d:/job_se/docker-compose.yml#L58)) to score documents based on keyword frequencies and inverse document frequencies.

### Hierarchical Navigable Small World (HNSW) Index
A high-dimensional vector graph indexing algorithm configured on PostgreSQL via pgvector (`idx_jobs_embedding_hnsw` with `m=16, ef_construction=64`) in [db/init/05_embeddings.sql:L18](file:///d:/job_se/db/init/05_embeddings.sql#L18).

### Reciprocal Rank Fusion (RRF)
A rank aggregation algorithm implemented in [ai/rag/retrievers/hybrid_retriever.py:L45](file:///d:/job_se/ai/rag/retrievers/hybrid_retriever.py#L45). Concurrently fuses dense vector search ranks and BM25 lexical ranks:
$$\text{RRF\_Score}(d) = \sum_{m \in \{\text{dense}, \text{bm25}\}} \frac{1}{60 + \text{rank}_m(d)}$$

### Skill Co-occurrence
Association mining query implemented in [db/init/02_master_data.sql:L74](file:///d:/job_se/db/init/02_master_data.sql#L74) measuring how frequently pairs of technical skills appear together within the same job description.

---

## 4. Acronyms & Abbreviations Matrix

| Acronym | Full Form | Codebase Relevance |
| :--- | :--- | :--- |
| **ATS** | Applicant Tracking System | Greenhouse, Lever, Ashby, Workable crawler modules. |
| **BM25** | Best Matching 25 | Elasticsearch lexical scoring algorithm. |
| **DLQ** | Dead-Letter Queue | Stream `raw-jobs-dlq` in `flows/dlq_handler.py`. |
| **DIP** | Dependency Inversion Principle | Clean Architecture decoupling in `core/ports/`. |
| **HNSW** | Hierarchical Navigable Small World | pgvector index algorithm on `jobs.embedding`. |
| **MTTR** | Mean Time to Resolve | Incident recovery metric for DLQ poison pills. |
| **RRF** | Reciprocal Rank Fusion | Rank fusion in `ai/rag/retrievers/hybrid_retriever.py`. |
| **SPOF** | Single Point of Failure | Architectural risk flagged for single datastore instances. |
| **TTFA** | Time to First Apply | UX candidate engagement telemetry metric. |

---

## 5. Change Log

| Version | Date | Author | Description of Changes |
| :--- | :--- | :--- | :--- |
| `1.0.0` | 2026-10-13 | Technical Writing Team | Complete alphabetical domain glossary, acronym matrix, and codebase definitions. |

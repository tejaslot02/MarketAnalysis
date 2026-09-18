# Plan: Remote 150K+ DS/AI/ML Job Collection & Analysis

## Goals

1. **Collect** remote Data Science / AI / ML job postings from 25+ sources
   (aggregators, remote boards, AI-specific boards, ATS platforms, comp sites).
2. **Normalize & dedupe** into a canonical record (cross-posting of the same
   role on multiple boards is common — Greenhouse/Lever/Ashby postings are
   mirrored by aggregators).
3. **Filter** to roles paying **≥ $150K USD** base/total comp (US remote).
4. **Enrich** with title canonicalization, skill extraction, seniority
   detection, and (optional) embeddings for semantic search.
5. **Serve & alert** via a query API, dashboards, and email/chat alerts.

## Assumptions

| # | Assumption | Validation |
|---|------------|------------|
| A1 | "Remote" means US-remote unless stated; non-US roles are out of scope | Filter by location strings + `remote_signals` |
| A2 | $150K+ means base **or** total comp ≥ 150K | Parse `salary_signals`; flag `base_vs_tc` |
| A3 | ATS public JSON APIs (Greenhouse/Lever/Ashby) remain stable | They are undocumented; monitor breakage |
| A4 | Aggregator scraping is rate-limited but feasible for metadata only | Respect robots.txt; back off |
| A5 | Salary is missing on many postings (esp. remote boards) | Cross-check via Levels.fyi/comprehensive.io |

## Pipeline

```
Ingestion → Normalization → Storage → Enrichment → Analysis → Serving
```

| Stage | Component | Input → Output |
|-------|-----------|----------------|
| Ingestion | Scrapy spiders + RSS/API adapters | portal data → raw JSON to Dragonfly (Redis Streams) + MinIO |
| Normalization | Spark batch / Python workers | raw JSON → canonical record |
| Dedup | Spark (hash on title+company+location) | duplicates collapsed |
| Storage | Postgres+pgvector, Elasticsearch, MinIO (lake) | canonical records persisted |
| Enrichment | Python (regex/NER over dictionaries) | title/seniority/skills/salary_ok |
| Analysis | SQL + Metabase + notebooks | aggregations, trends |
| Serving | FastAPI + Metabase + alerts | queries, dashboards, notifications |

## Phased Roadmap

### Phase 0 — Setup (this repo)
- [x] Dictionaries (portals, titles, skills, keywords, responsibilities)
- [x] Docker toolchain (Postgres+pgvector, Dragonfly, Spark, MinIO, Prefect,
      Elasticsearch, Jupyter, Metabase, FastAPI, Prometheus, Grafana)
- [ ] `docker compose up` green

### Phase 1 — Ingestion
- [ ] ATS adapters first (Greenhouse, Lever, Ashby) — highest signal, API-first
- [ ] API remote boards (RemoteOK, Remotive)
- [ ] RSS (We Work Remotely)
- [ ] HN "Who is hiring" via HN Firebase API
- [ ] Polite HTML scrapers for aijobs.net, Built In, Dice (rate-limited)

### Phase 2 — Normalization + Dedup
- [ ] Map every source to canonical schema
- [ ] Stable IDs (`sha256(source:external_id)`)
- [ ] Dedup by (normalized title + normalized company + location)
- [ ] Archive raw records to MinIO (parquet)

### Phase 3 — Salary Extraction + 150K Filter
- [ ] Regex over `salary_signals` (e.g. `$180,000 - $220,000`, `200k`)
- [ ] Infer annual from hourly (`$90/hr` → ~187K)
- [ ] Set `salary_ok = salary_min >= 150000 OR salary_max >= 150000`
- [ ] For missing salary: cross-check Levels.fyi / comprehensive.io

### Phase 4 — NLP / Skill Matching
- [ ] Title → `title_canonical` via `job_titles.yaml` synonyms
- [ ] Seniority detection via `seniority_signals`
- [ ] Skill extraction via `skills_technologies.yaml` aliases
- [ ] Responsibility phrase matching via `roles_responsibilities.yaml`
- [ ] Embeddings (pgvector) for semantic search over descriptions

### Phase 5 — Serving / UI / Alerts
- [ ] FastAPI `/jobs`, `/stats`, semantic search
- [ ] Metabase dashboards (volume by title, salary distribution, source health)
- [ ] Prefect-scheduled refresh + quality checks
- [ ] Alerts (email/Slack) for new 150K+ remote matches

## Success Metrics

| Metric | Target |
|--------|--------|
| Sources live | ≥ 15 |
| New postings / week | ≥ 500 |
| Postings with parsed salary | ≥ 40% |
| Duplicate rate after dedup | < 5% |
| 150K+ recall (vs manual spot-check) | ≥ 90% |
| Pipeline end-to-end latency | < 30 min |
| Scraper uptime / no-blocks | ≥ 95% |

## Canonical Job Record (SQL DDL)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE jobs (
    id              TEXT PRIMARY KEY,                 -- sha256(source + external_id)
    source          TEXT NOT NULL,                    -- greenhouse, lever, remoteok, ...
    external_id     TEXT,
    title           TEXT NOT NULL,
    company         TEXT,
    location        TEXT,
    is_remote       BOOLEAN DEFAULT FALSE,
    remote_type     TEXT,                             -- fully_remote | hybrid | on_site
    salary_min      NUMERIC,
    salary_max      NUMERIC,
    salary_currency TEXT DEFAULT 'USD',
    salary_raw      TEXT,
    base_vs_tc      TEXT,                             -- base | total_comp | unknown
    posted_at       TIMESTAMPTZ,
    first_seen_at   TIMESTAMPTZ DEFAULT now(),
    last_seen_at    TIMESTAMPTZ DEFAULT now(),
    expires_at      TIMESTAMPTZ,
    description     TEXT,
    url             TEXT,
    seniority       TEXT,                             -- staff | principal | lead | manager | ...
    title_canonical TEXT,
    skills          JSONB DEFAULT '[]',
    responsibilities JSONB DEFAULT '[]',
    salary_ok       BOOLEAN DEFAULT FALSE,            -- salary_min >= 150000 OR salary_max >= 150000; FALSE when unknown
    embedding       vector(1536),
    raw             JSONB
);
```

> The live DDL is in `db/init/01_schema.sql` (auto-loaded on first Postgres
> start). Keep this doc in sync with that file.

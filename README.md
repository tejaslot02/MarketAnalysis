# Remote 150K+ DS/AI/ML Job Search Platform

Collect, normalize, and analyze **remote Data Science / AI / ML job postings
paying $150K+ USD** (US market) using a Docker-based big-data toolchain.

> **Disclaimer** — Personal/educational project for your own job search.
> Respect robots.txt, Terms of Service, and rate limits. Do not scrape
> LinkedIn or paywalled content. See `docs/COMPLIANCE.md`.

## Quick Start

```bash
cp .env.example .env        # adjust secrets
make up                     # or: docker compose up -d

# Wait for services, then verify:
docker compose ps
curl http://localhost:8000/health
curl "http://localhost:8000/jobs?min_salary=150000&remote=true"

make seed-db                # load sample rows
make init-prefect           # (optional) re-run Prefect DB migrations
```

## Service URLs

| Service | URL |
|---------|-----|
| FastAPI | http://localhost:8000/docs |
| Metabase | http://localhost:3001 |
| Jupyter | http://localhost:8888 |
| Prefect UI | http://localhost:4200 |
| MinIO console | http://localhost:9001 |
| Spark master UI | http://localhost:8080 |
| Grafana | http://localhost:3000 (admin/admin) |
| Prometheus | http://localhost:9090 |
| Elasticsearch | http://localhost:9200 |

## Directory Map

```
.
├── data/dictionaries/          # YAML dictionaries (portals, titles, skills, keywords)
│   ├── job_portals.yaml
│   ├── job_titles.yaml
│   ├── roles_responsibilities.yaml
│   ├── skills_technologies.yaml
│   └── search_keywords.yaml
├── db/
│   ├── init/                   # auto-loaded on first Postgres start
│   └── seed/                   # sample rows (make seed-db)
├── api/                        # FastAPI service
├── scrapers/                   # Scrapy adapters + Dockerfile
├── flows/                      # Prefect flows (consume-raw-jobs, etc.)
├── notebooks/                  # Jupyter workdir
├── monitoring/prometheus.yml
├── docs/
│   ├── PLAN.md                 # end-to-end plan, roadmap, schema
│   ├── ARCHITECTURE.md         # C4 + data-flow diagrams
│   └── COMPLIANCE.md           # scraping ethics & legal notes
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

## Stack

Postgres+pgvector · Elasticsearch · Dragonfly (Redis Streams) · MinIO · Spark ·
Prefect · Jupyter · Metabase · FastAPI · Prometheus · Grafana.

See `docs/ARCHITECTURE.md` for diagrams and rationale, and `docs/PLAN.md` for
phases, metrics, and the canonical job schema.

## Make targets

`up` · `down` · `logs` · `ps` · `init-prefect` · `migrate` · `seed-master` · `prefect-flows` · `seed-db` · `scrape` · `scrape-all` · `venv` · `test` · `reset` · `clean`

## Scheduling & Master Data

- **Daily refresh** is handled by the `prefect-scheduler` service (`flows/scheduler.py`, Prefect 3 `prefect.serve`):
  - `seed-master-data` -> daily 06:30 America/New_York (`SEED_CRON`)
  - `scrape-portals` -> daily 07:00 America/New_York (`SCRAPE_CRON`)
  - `consume-raw-jobs` -> every 30 min (`CONSUME_INTERVAL_SECONDS`)
- **Portals**: 10 live adapters (greenhouse, lever, ashby, workable, remoteok, remotive, weworkremotely, hn, aijobs, builtin). ATS spiders fan out across the company list in `data/dictionaries/companies.yaml`.
- **Skill database**: seeded from `data/dictionaries/skills_technologies.yaml` into the `skills` table; skill frequency and co-occurrence are exposed as `skill_frequency` / `skill_cooccurrence` views.
- **Master data**: `companies`, `portals`, `skills`, `job_titles`, and `portal_runs` tables (see `db/init/02_master_data.sql`). Apply to an existing volume with `make migrate`, then `make seed-master`.
- **Dashboard**: Metabase reads these tables/views; run `docker compose exec -T prefect-scheduler python - < scripts/setup_metabase.py` to (re)provision cards.



## Testing

```bash
make venv    # create .venv + install requirements-dev.txt
make test    # run pytest (see docs/TEST_CASES.md)
```

## Observability

- **Prefect metrics**: `PREFECT_API_ENABLE_METRICS=true` exposes Prometheus metrics
  at `http://localhost:4200/metrics` (scraped by the `prefect` job in
  `monitoring/prometheus.yml`).
- **Grafana**: Prometheus datasource + `ETL Dashboards` are provisioned from
  `monitoring/grafana/` (login admin/admin at http://localhost:3100).
- **Prefect UI**: served at http://localhost:4200 (API reachable via
  `PREFECT_UI_API_URL=http://localhost:4200/api`).

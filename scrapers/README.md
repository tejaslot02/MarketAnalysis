# Scrapers

Per-portal adapters that fetch remote 150K+ DS/AI/ML job postings and emit a
canonical job record to **Dragonfly (Redis Streams)** and/or **MinIO** (raw archive).

## Pattern

Each portal is a Scrapy spider in `portals/`. Every spider is responsible for:

1. **Fetching** — prefer official APIs (Greenhouse, Lever, Ashby, RemoteOK,
   Remotive). Fall back to HTML scraping only when no API exists.
2. **Normalizing** — map the source record to the canonical schema
   (see `docs/PLAN.md`), producing a stable `id` from `source + external_id`.
3. **Emitting** — yield the record; the producer (`run.py`) XADDs the canonical
   JSON record to the Dragonfly stream `raw-jobs`. The Prefect flow
   `consume-raw-jobs` (`flows/scrape_flow.py`) consumes the stream and persists
   records to Postgres/MinIO.

## Adapter checklist

- [ ] Prefer API over HTML (lower ToS risk, more stable).
- [ ] Respect `robots.txt` and published rate limits.
- [ ] Rotate `User-Agent`; add `From`/contact info (see `.env.example`).
- [ ] Back off exponentially on 429/503; never hammer a host.
- [ ] Do not scrape gated/paywalled content (e.g. FlexJobs full listings).
- [ ] Store only public metadata (title, company, location, salary, URL) —
      no personal data (see `docs/COMPLIANCE.md`).

## Output schema (JSON Lines)

One JSON object per line, matching `db/init/01_schema.sql`:

```json
{
  "id": "sha256(greenhouse:companyname:12345)",
  "source": "greenhouse",
  "external_id": "12345",
  "title": "Senior Machine Learning Engineer",
  "company": "companyname",
  "location": "Remote (US)",
  "is_remote": true,
  "remote_type": "fully_remote",
  "salary_min": 180000,
  "salary_max": 220000,
  "salary_currency": "USD",
  "salary_raw": "$180,000 - $220,000",
  "base_vs_tc": "base",
  "posted_at": "2024-06-01T00:00:00Z",
  "description": "...",
  "url": "https://boards.greenhouse.io/companyname/jobs/12345",
  "seniority": null,
  "title_canonical": null,
  "skills": [],
  "responsibilities": [],
  "salary_ok": false,
  "raw": { }
}
```

## Running a spider locally

```bash
# Inside the container or a venv with the requirements installed:
scrapy runspider scrapers/portals/example_spider.py -a board_token=companyname
```

## Adding a new portal

1. Add its metadata to `data/dictionaries/job_portals.yaml`.
2. Create `portals/<name>_spider.py` following `example_spider.py`.
3. Add a scheduling entry in a Prefect flow (`flows/`).

-- Master-data dimension tables + mining views.
-- Idempotent: safe to re-run (CREATE TABLE IF NOT EXISTS / CREATE OR REPLACE VIEW).
-- Loaded automatically on first Postgres start; for existing volumes run `make migrate`.

-- Companies: seeded from data/dictionaries/companies.yaml + auto-discovered from jobs.
CREATE TABLE IF NOT EXISTS companies (
    id               TEXT PRIMARY KEY,               -- normalized slug
    name             TEXT NOT NULL,
    greenhouse_token TEXT,
    lever_slug       TEXT,
    ashby_org        TEXT,
    workable_account TEXT,
    first_seen_at    TIMESTAMPTZ DEFAULT now(),
    last_seen_at     TIMESTAMPTZ DEFAULT now()
);

-- Portals: the portal catalog (mirror of data/dictionaries/job_portals.yaml).
CREATE TABLE IF NOT EXISTS portals (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT,                             -- aggregator | remote_board | ai_specific | ats | compensation
    url             TEXT,
    priority        TEXT,                             -- high | medium | low
    scraping_method TEXT,                             -- api | scrape | rss | manual
    api             TEXT,                             -- yes | restricted | no
    salary_data     BOOLEAN DEFAULT FALSE,
    remote_filter   BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT TRUE
);

-- Skills: the skill database (mirror of data/dictionaries/skills_technologies.yaml).
CREATE TABLE IF NOT EXISTS skills (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    category    TEXT,
    subcategory TEXT,
    weight      INTEGER DEFAULT 5
);

-- Job titles: canonical titles + synonyms (mirror of data/dictionaries/job_titles.yaml).
CREATE TABLE IF NOT EXISTS job_titles (
    id        TEXT PRIMARY KEY,
    canonical TEXT NOT NULL UNIQUE,
    track     TEXT,                                   -- individual_contributor | mlops_platform | research | leadership
    synonyms  JSONB DEFAULT '[]'
);

-- Portal runs: ingestion health / freshness (written by flows/scrape_portals.py).
CREATE TABLE IF NOT EXISTS portal_runs (
    id           BIGSERIAL PRIMARY KEY,
    portal       TEXT NOT NULL,
    started_at   TIMESTAMPTZ DEFAULT now(),
    finished_at  TIMESTAMPTZ,
    status       TEXT DEFAULT 'running',              -- running | success | error
    jobs_emitted INTEGER DEFAULT 0,
    error        TEXT
);

CREATE INDEX IF NOT EXISTS idx_portal_runs_portal ON portal_runs (portal, finished_at DESC);
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies (name);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills (category);

-- ---- Mining views ----------------------------------------------------------

-- Skill frequency: how often each skill appears across job postings.
CREATE OR REPLACE VIEW skill_frequency AS
SELECT s->>'name'     AS skill,
       s->>'category' AS category,
       COUNT(*)       AS job_count,
       ROUND(AVG((s->>'weight')::int), 1) AS avg_weight
FROM jobs, jsonb_array_elements(skills) AS s
GROUP BY 1, 2;

-- Skill co-occurrence: association mining over skill pairs within the same posting.
CREATE OR REPLACE VIEW skill_cooccurrence AS
WITH pairs AS (
    SELECT j.id,
           a.s->>'name' AS skill_a,
           b.s->>'name' AS skill_b
    FROM jobs j,
         jsonb_array_elements(j.skills) AS a(s),
         jsonb_array_elements(j.skills) AS b(s)
    WHERE a.s->>'name' < b.s->>'name'
)
SELECT skill_a, skill_b, COUNT(*) AS co_count
FROM pairs
GROUP BY 1, 2
ORDER BY co_count DESC;

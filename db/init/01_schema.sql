-- Canonical job posting schema (initial).
-- Loaded automatically on first postgres container start.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,                 -- stable hash of source + external_id
    source          TEXT NOT NULL,                    -- e.g. greenhouse, lever, remoteok
    external_id     TEXT,                             -- id at the source
    title           TEXT NOT NULL,
    company         TEXT,
    location        TEXT,                              -- 'Remote (US)' etc.
    is_remote       BOOLEAN DEFAULT FALSE,
    remote_type     TEXT,                              -- fully_remote | hybrid | on_site
    salary_min      NUMERIC,
    salary_max      NUMERIC,
    salary_currency TEXT DEFAULT 'USD',
    salary_raw      TEXT,                              -- raw string as posted
    base_vs_tc      TEXT,                              -- base | total_comp | unknown
    posted_at       TIMESTAMPTZ,
    first_seen_at   TIMESTAMPTZ DEFAULT now(),
    last_seen_at    TIMESTAMPTZ DEFAULT now(),
    expires_at      TIMESTAMPTZ,
    description     TEXT,                              -- full raw description
    url             TEXT,
    seniority       TEXT,                              -- mid | senior | staff | principal | lead | manager | director | vp | c_level
    title_canonical TEXT,                              -- matched canonical title from dictionary
    skills          JSONB DEFAULT '[]',                -- matched skills (name -> weight)
    responsibilities JSONB DEFAULT '[]',               -- matched responsibility phrases
    salary_ok       BOOLEAN DEFAULT FALSE,             -- TRUE if salary_min >= 150000 OR salary_max >= 150000; FALSE when salary unknown
    embedding       vector(1536),                      -- semantic search embedding (populated by enrichment)
    raw             JSONB                              -- full normalized source record
);

CREATE INDEX IF NOT EXISTS idx_jobs_salary ON jobs (salary_min) WHERE salary_min IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_jobs_remote ON jobs (is_remote);
CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs (title_canonical);
CREATE INDEX IF NOT EXISTS idx_jobs_posted ON jobs (posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_embedding ON jobs USING hnsw (embedding vector_cosine_ops);

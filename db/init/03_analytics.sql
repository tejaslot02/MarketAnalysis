-- Daily analytics snapshots + trend views (skill/title/company/source trends).
-- Idempotent: safe to re-run. Loaded on fresh init; for existing volumes run `make migrate`.

CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id               BIGSERIAL PRIMARY KEY,
    snapshot_date    DATE NOT NULL UNIQUE,
    total_jobs       INTEGER,
    remote_jobs      INTEGER,
    jobs_with_skills INTEGER,
    companies        INTEGER,
    above_150k       INTEGER
);

CREATE TABLE IF NOT EXISTS skill_trend (
    id            BIGSERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    skill         TEXT NOT NULL,
    category      TEXT,
    job_count     INTEGER DEFAULT 0,
    UNIQUE (snapshot_date, skill)
);

CREATE TABLE IF NOT EXISTS title_trend (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL,
    title_canonical TEXT NOT NULL,
    job_count       INTEGER DEFAULT 0,
    UNIQUE (snapshot_date, title_canonical)
);

CREATE TABLE IF NOT EXISTS company_hiring (
    id            BIGSERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    company       TEXT NOT NULL,
    jobs_active   INTEGER DEFAULT 0,
    jobs_new      INTEGER DEFAULT 0,
    UNIQUE (snapshot_date, company)
);

CREATE TABLE IF NOT EXISTS source_trend (
    id            BIGSERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    source        TEXT NOT NULL,
    job_count     INTEGER DEFAULT 0,
    UNIQUE (snapshot_date, source)
);

CREATE INDEX IF NOT EXISTS idx_skill_trend_date ON skill_trend (snapshot_date);
CREATE INDEX IF NOT EXISTS idx_title_trend_date ON title_trend (snapshot_date);
CREATE INDEX IF NOT EXISTS idx_company_hiring_date ON company_hiring (snapshot_date);
CREATE INDEX IF NOT EXISTS idx_source_trend_date ON source_trend (snapshot_date);

-- Emerging skills: growth between the earliest and latest snapshot.
CREATE OR REPLACE VIEW skill_momentum AS
WITH bounds AS (
    SELECT MIN(snapshot_date) AS first_d, MAX(snapshot_date) AS last_d FROM skill_trend
),
first AS (SELECT skill, job_count FROM skill_trend WHERE snapshot_date = (SELECT first_d FROM bounds)),
last  AS (SELECT skill, job_count FROM skill_trend WHERE snapshot_date = (SELECT last_d FROM bounds))
SELECT l.skill,
       COALESCE(f.job_count, 0) AS first_count,
       l.job_count AS latest_count,
       (l.job_count - COALESCE(f.job_count, 0)) AS delta,
       CASE WHEN COALESCE(f.job_count, 0) = 0 THEN NULL
            ELSE ROUND(100.0 * (l.job_count - f.job_count) / f.job_count, 1) END AS pct_change
FROM last l LEFT JOIN first f USING (skill)
ORDER BY delta DESC;

-- Salary benchmarks from postings that actually list a range.
CREATE OR REPLACE VIEW salary_benchmark AS
SELECT COALESCE(title_canonical, 'Unclassified') AS title,
       COALESCE(seniority, 'unknown')          AS seniority,
       COUNT(*)                                AS n,
       ROUND(AVG(salary_min), 0)               AS avg_min,
       ROUND(AVG(salary_max), 0)               AS avg_max,
       MIN(salary_min)                         AS min_salary,
       MAX(salary_max)                         AS max_salary
FROM jobs
WHERE salary_min IS NOT NULL OR salary_max IS NOT NULL
GROUP BY 1, 2;

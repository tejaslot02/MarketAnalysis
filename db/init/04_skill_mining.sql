-- Skill-bank enrichment: mined candidate skills (for review/promotion).
-- Idempotent. Loaded on fresh init; for existing volumes run `make migrate`.

CREATE TABLE IF NOT EXISTS skill_candidates (
    id              BIGSERIAL PRIMARY KEY,
    term            TEXT NOT NULL UNIQUE,
    frequency       INTEGER DEFAULT 0,
    sample_contexts JSONB DEFAULT '[]',
    first_seen_at   TIMESTAMPTZ DEFAULT now(),
    last_seen_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_skill_candidates_freq ON skill_candidates (frequency DESC);

-- Candidates not yet present in the skill bank (by name).
CREATE OR REPLACE VIEW new_skill_candidates AS
SELECT c.term, c.frequency, c.sample_contexts
FROM skill_candidates c
LEFT JOIN skills s ON lower(s.name) = lower(c.term)
WHERE s.id IS NULL
ORDER BY c.frequency DESC;

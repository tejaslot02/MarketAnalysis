-- Embeddings & Semantic Search Initialization (05_embeddings.sql)
-- Ensures vector extension, HNSW cosine index tuning, and semantic query functions.

CREATE EXTENSION IF NOT EXISTS vector;

-- Ensure embedding vector column on jobs table (1536-dim text-embedding-3-small)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'jobs' AND column_name = 'embedding'
    ) THEN
        ALTER TABLE jobs ADD COLUMN embedding vector(1536);
    END IF;
END $$;

-- Tuned HNSW vector index for high-recall cosine similarity search
CREATE INDEX IF NOT EXISTS idx_jobs_embedding_hnsw 
ON jobs USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Helper function for semantic search with cosine distance operator <=>
CREATE OR REPLACE FUNCTION match_jobs_by_vector(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 50
)
RETURNS TABLE (
    id TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    is_remote BOOLEAN,
    salary_min NUMERIC,
    salary_max NUMERIC,
    posted_at TIMESTAMPTZ,
    url TEXT,
    seniority TEXT,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        j.id,
        j.title,
        j.company,
        j.location,
        j.is_remote,
        j.salary_min,
        j.salary_max,
        j.posted_at,
        j.url,
        j.seniority,
        1 - (j.embedding <=> query_embedding) AS similarity
    FROM jobs j
    WHERE j.embedding IS NOT NULL
      AND (1 - (j.embedding <=> query_embedding)) >= match_threshold
    ORDER BY j.embedding <=> query_embedding ASC
    LIMIT match_count;
$$;

-- View tracking vector embedding coverage
CREATE OR REPLACE VIEW vw_embedding_coverage AS
SELECT
    COUNT(*) AS total_jobs,
    COUNT(embedding) AS embedded_jobs,
    COUNT(*) - COUNT(embedding) AS pending_embedding,
    ROUND((COUNT(embedding)::decimal / NULLIF(COUNT(*), 0)) * 100, 2) AS coverage_percent
FROM jobs;

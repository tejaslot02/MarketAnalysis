"""Prefect flow to batch embed unembedded job postings into pgvector."""
from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai.adapters.embeddings.openai_embedder import OpenAIEmbedder
from ai.rag.embedders.pipeline import EmbeddingPipeline
from ai.rag.vector_stores.pgvector_store import PgVectorStore
from config.settings import get_settings
from prefect import flow

settings = get_settings()


@flow(name="embed-unembedded-jobs")
async def embed_jobs_flow(batch_size: int = 50, limit: int = 200) -> int:
    """Identify jobs lacking vector embeddings, generate embeddings, and persist to pgvector."""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    embedder = OpenAIEmbedder(
        api_key=settings.openai_api_key,
        model=settings.openai_embedding_model,
        dimension=settings.embedding_dimension,
    )
    pipeline = EmbeddingPipeline(embedder, batch_size=batch_size)
    vector_store = PgVectorStore(engine)

    query = """
        SELECT id, title, company, seniority, skills, description
        FROM jobs
        WHERE embedding IS NULL
        ORDER BY posted_at DESC NULLS LAST
        LIMIT :limit
    """

    jobs: list[dict[str, Any]] = []
    async with engine.connect() as conn:
        rows = (await conn.execute(text(query), {"limit": limit})).mappings().all()
        jobs = [dict(r) for r in rows]

    if not jobs:
        print("[embed_jobs_flow] No unembedded jobs found.")
        await engine.dispose()
        return 0

    print(f"[embed_jobs_flow] Generating embeddings for {len(jobs)} jobs...")
    embedded_pairs = await pipeline.embed_jobs(jobs)

    ids = [p[0] for p in embedded_pairs]
    vectors = [p[1] for p in embedded_pairs]

    await vector_store.add_vectors(ids, vectors)
    print(f"[embed_jobs_flow] Successfully saved {len(ids)} embeddings to pgvector.")

    await engine.dispose()
    return len(ids)


if __name__ == "__main__":
    count = asyncio.run(embed_jobs_flow())
    print(f"Embedding flow completed. Processed: {count}")

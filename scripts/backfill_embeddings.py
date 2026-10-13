"""CLI maintenance script to backfill dense vector embeddings for historic jobs."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai.adapters.embeddings.openai_embedder import OpenAIEmbedder
from ai.adapters.embeddings.sentence_transformer import SentenceTransformerEmbedder
from ai.rag.embedders.pipeline import EmbeddingPipeline
from ai.rag.vector_stores.pgvector_store import PgVectorStore
from config.settings import get_settings


async def run_backfill(
    provider_name: str, batch_size: int, total_limit: int | None = None
) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    if provider_name == "openai":
        embedder = OpenAIEmbedder(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimension=settings.embedding_dimension,
        )
    else:
        embedder = SentenceTransformerEmbedder(
            model_name=settings.local_embedding_model,
            dimension=384,
        )

    pipeline = EmbeddingPipeline(embedder, batch_size=batch_size)
    vector_store = PgVectorStore(engine)

    total_processed = 0
    while True:
        limit = min(batch_size * 2, total_limit - total_processed) if total_limit else batch_size * 2
        if limit <= 0:
            break

        query = """
            SELECT id, title, company, seniority, skills, description
            FROM jobs
            WHERE embedding IS NULL
            ORDER BY posted_at DESC NULLS LAST
            LIMIT :limit
        """
        async with engine.connect() as conn:
            rows = (await conn.execute(text(query), {"limit": limit})).mappings().all()
            batch = [dict(r) for r in rows]

        if not batch:
            print("[backfill] No more unembedded jobs found.")
            break

        pairs = await pipeline.embed_jobs(batch)
        ids = [p[0] for p in pairs]
        vectors = [p[1] for p in pairs]

        await vector_store.add_vectors(ids, vectors)
        total_processed += len(ids)
        print(f"[backfill] Processed {len(ids)} jobs (Total so far: {total_processed})")

        if total_limit and total_processed >= total_limit:
            break

    await engine.dispose()
    print(f"[backfill] Finished backfill. Total embedded jobs: {total_processed}")


def main():
    parser = argparse.ArgumentParser(description="Backfill pgvector job embeddings.")
    parser.add_argument(
        "--provider",
        choices=["openai", "local"],
        default="openai",
        help="Embedding provider",
    )
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size")
    parser.add_argument("--limit", type=int, default=None, help="Max total jobs to process")

    args = parser.parse_args()
    asyncio.run(run_backfill(args.provider, args.batch_size, args.limit))


if __name__ == "__main__":
    main()

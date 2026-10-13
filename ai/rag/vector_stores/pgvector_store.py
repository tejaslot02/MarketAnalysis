"""PgVector storage adapter implementing VectorStore protocol."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from core.ports.vector_store import VectorStore


class PgVectorStore(VectorStore):
    """PostgreSQL + pgvector storage implementation."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def add_vectors(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        if not ids or not vectors:
            return

        async with self.engine.begin() as conn:
            for job_id, vec in zip(ids, vectors):
                # Format vector as pgvector string e.g. '[0.1, 0.2, ...]'
                vec_str = "[" + ",".join(str(x) for x in vec) + "]"
                await conn.execute(
                    text("UPDATE jobs SET embedding = CAST(:vec AS vector) WHERE id = :id"),
                    {"vec": vec_str, "id": job_id},
                )

    async def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        vec_str = "[" + ",".join(str(x) for x in query_vector) + "]"
        clauses = ["embedding IS NOT NULL"]
        params: dict[str, Any] = {"vec": vec_str, "limit": top_k}

        if filters:
            if filters.get("min_salary") is not None:
                clauses.append("salary_min >= :min_salary")
                params["min_salary"] = filters["min_salary"]
            if filters.get("remote") is not None:
                clauses.append("is_remote = :remote")
                params["remote"] = bool(filters["remote"])
            if filters.get("seniority"):
                clauses.append("seniority = :seniority")
                params["seniority"] = filters["seniority"]
            if filters.get("title"):
                clauses.append("title ILIKE :title")
                params["title"] = f"%{filters['title']}%"

        where_clause = " WHERE " + " AND ".join(clauses)
        query = f"""
            SELECT id, title, company, location, is_remote, salary_min, salary_max,
                   salary_currency, posted_at, url, seniority,
                   (1 - (embedding <=> CAST(:vec AS vector))) AS similarity_score
            FROM jobs
            {where_clause}
            ORDER BY embedding <=> CAST(:vec AS vector) ASC
            LIMIT :limit
        """

        try:
            async with self.engine.connect() as conn:
                rows = (await conn.execute(text(query), params)).mappings().all()
                return [dict(r) for r in rows]
        except Exception:
            return []

"""BM25 lexical retriever using Elasticsearch with SQL text search fallback."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from ai.rag.vector_stores.elasticsearch_store import ElasticsearchStore


class BM25Retriever:
    """Full-text lexical search retriever."""

    def __init__(
        self,
        es_store: ElasticsearchStore | None = None,
        db_engine: AsyncEngine | None = None,
    ):
        self.es_store = es_store
        self.db_engine = db_engine

    async def retrieve(
        self, query: str, top_k: int = 50, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if not query.strip():
            return []

        # 1. Try Elasticsearch BM25 if available
        if self.es_store:
            try:
                hits = await self.es_store.search_bm25(query, top_k=top_k)
                if hits:
                    return hits
            except Exception:
                pass

        # 2. Fallback to SQL ILIKE text search if engine is provided
        if self.db_engine:
            clauses = ["(title ILIKE :q OR description ILIKE :q)"]
            params: dict[str, Any] = {"q": f"%{query}%", "limit": top_k}
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

            where = " WHERE " + " AND ".join(clauses)
            sql = f"""
                SELECT id, title, company, location, is_remote, salary_min, salary_max,
                       salary_currency, posted_at, url, seniority, 1.0 AS bm25_score
                FROM jobs
                {where}
                ORDER BY posted_at DESC NULLS LAST
                LIMIT :limit
            """
            try:
                async with self.db_engine.connect() as conn:
                    rows = (await conn.execute(text(sql), params)).mappings().all()
                    return [dict(r) for r in rows]
            except Exception:
                return []

        return []

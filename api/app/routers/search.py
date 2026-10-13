"""Hybrid and semantic search router combining dense vectors and BM25 lexical ranking."""
from __future__ import annotations

from typing import Any

from elasticsearch import Elasticsearch
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ai.adapters.embeddings.openai_embedder import OpenAIEmbedder
from ai.rag.retrievers.bm25_retriever import BM25Retriever
from ai.rag.retrievers.hybrid_retriever import HybridRetriever
from ai.rag.retrievers.vector_retriever import VectorRetriever
from ai.rag.vector_stores.elasticsearch_store import ElasticsearchStore
from ai.rag.vector_stores.pgvector_store import PgVectorStore
from api.app.dependencies.db import get_async_engine
from api.app.schemas.search import SearchResponse, SearchResultItem
from config.settings import get_settings

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=SearchResponse)
async def search_jobs(
    q: str = Query(..., min_length=1, description="Semantic or lexical search query"),
    min_salary: int | None = Query(None, ge=0, description="Minimum annual salary in USD"),
    remote: bool | None = Query(None, description="Filter by remote flag"),
    seniority: str | None = Query(None, description="senior|staff|principal|lead|manager|director"),
    hybrid: bool | None = Query(None, description="Force enable/disable hybrid RRF fusion"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Execute hybrid dense-vector and BM25 search with automatic ILIKE fallback."""
    settings = get_settings()
    engine = get_async_engine()

    should_use_hybrid = hybrid if hybrid is not None else settings.use_vector_search
    filters: dict[str, Any] = {}
    if min_salary is not None:
        filters["min_salary"] = min_salary
    if remote is not None:
        filters["remote"] = remote
    if seniority:
        filters["seniority"] = seniority

    # If hybrid search is requested and enabled
    if should_use_hybrid:
        try:
            embedder = OpenAIEmbedder(
                api_key=settings.openai_api_key,
                model=settings.openai_embedding_model,
                dimension=settings.embedding_dimension,
            )
            pg_store = PgVectorStore(engine)
            vector_retriever = VectorRetriever(pg_store, embedder)

            # Optional ES store
            es_client = None
            try:
                es_client = Elasticsearch([settings.elasticsearch_url])
            except Exception:
                pass
            es_store = ElasticsearchStore(es_client, index_name=settings.es_index)
            bm25_retriever = BM25Retriever(es_store=es_store, db_engine=engine)

            retriever = HybridRetriever(vector_retriever, bm25_retriever)
            fused_results = await retriever.retrieve(q, top_k=limit + offset, filters=filters)
            sliced = fused_results[offset : offset + limit]

            formatted = [
                SearchResultItem(
                    id=doc.get("id", ""),
                    title=doc.get("title", ""),
                    company=doc.get("company"),
                    location=doc.get("location"),
                    is_remote=bool(doc.get("is_remote", False)),
                    remote_type=doc.get("remote_type"),
                    salary_min=doc.get("salary_min"),
                    salary_max=doc.get("salary_max"),
                    salary_currency=doc.get("salary_currency", "USD"),
                    posted_at=doc.get("posted_at"),
                    url=doc.get("url"),
                    seniority=doc.get("seniority"),
                    rrf_score=doc.get("rrf_score"),
                    similarity_score=doc.get("similarity_score"),
                    match_type="hybrid",
                )
                for doc in sliced
            ]
            return {
                "query": q,
                "count": len(formatted),
                "limit": limit,
                "offset": offset,
                "engine": "hybrid_rrf",
                "results": formatted,
            }
        except Exception:
            # Fallback to lexical SQL path if hybrid retriever pipeline encounters error
            pass

    # Standard SQL ILIKE fallback path
    clauses = ["(title ILIKE :q OR description ILIKE :q)"]
    params: dict[str, Any] = {"q": f"%{q}%", "limit": limit, "offset": offset}
    if min_salary is not None:
        clauses.append("salary_min >= :min_salary")
        params["min_salary"] = min_salary
    if remote is not None:
        clauses.append("is_remote = :remote")
        params["remote"] = remote
    if seniority:
        clauses.append("seniority = :seniority")
        params["seniority"] = seniority

    where = " WHERE " + " AND ".join(clauses)
    query = f"""
        SELECT id, title, company, location, is_remote, remote_type,
               salary_min, salary_max, salary_currency, posted_at, url, seniority
        FROM jobs
        {where}
        ORDER BY posted_at DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """

    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(text(query), params)).mappings().all()
            jobs = [
                SearchResultItem(
                    id=r["id"],
                    title=r["title"],
                    company=r["company"],
                    location=r["location"],
                    is_remote=bool(r["is_remote"]),
                    remote_type=r["remote_type"],
                    salary_min=r["salary_min"],
                    salary_max=r["salary_max"],
                    salary_currency=r["salary_currency"] or "USD",
                    posted_at=r["posted_at"],
                    url=r["url"],
                    seniority=r["seniority"],
                    bm25_score=1.0,
                    match_type="keyword",
                )
                for r in rows
            ]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc

    return {
        "query": q,
        "count": len(jobs),
        "limit": limit,
        "offset": offset,
        "engine": "ilike_fallback",
        "results": jobs,
    }

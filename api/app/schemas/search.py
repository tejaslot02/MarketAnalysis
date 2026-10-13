"""Pydantic schemas for search queries and hybrid retrieval results."""
from __future__ import annotations

from pydantic import BaseModel

from api.app.schemas.job import JobSummary


class SearchResultItem(JobSummary):
    """Job result item annotated with retrieval score and engine type."""
    similarity_score: float | None = None
    bm25_score: float | None = None
    rrf_score: float | None = None
    match_type: str = "keyword"  # keyword | semantic | hybrid


class SearchResponse(BaseModel):
    """Response envelope for hybrid and vector search."""
    query: str
    count: int
    limit: int
    offset: int
    engine: str  # hybrid_rrf | pgvector_cosine | ilike_fallback
    results: list[SearchResultItem]

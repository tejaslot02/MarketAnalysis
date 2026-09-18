"""Minimal FastAPI service for the job-search platform.

Endpoints:
  GET /health  - liveness + DB connectivity
  GET /jobs     - filtered job listing (Postgres/pgvector)
  GET /stats    - aggregate statistics

Semantic search (/jobs?q=...) currently falls back to keyword matching;
the pgvector cosine path is ready once embeddings are populated (see
embedding column in db/init/01_schema.sql).
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Response
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/jobs",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

app = FastAPI(title="Job Search API", version="1.0.0")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _fetch_all(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(text(query), params or {}).mappings().all()
        return [dict(r) for r in rows]


def _fetch_one(query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    with engine.connect() as conn:
        row = conn.execute(text(query), params or {}).mappings().first()
        return dict(row) if row else None


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health")
def health(response: Response) -> dict[str, Any]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = 503
        return {"status": "degraded", "database": "unavailable"}
    return {"status": "ok", "database": "ok"}


@app.get("/jobs")
def list_jobs(
    title: str | None = Query(None, description="Title substring (e.g. 'machine learning engineer')"),
    skill: str | None = Query(None, description="Required skill (e.g. 'pytorch')"),
    min_salary: int | None = Query(None, ge=0, description="Minimum annual salary in USD"),
    remote: bool | None = Query(None, description="Filter by remote flag"),
    seniority: str | None = Query(None, description="senior|staff|principal|lead|manager|director"),
    q: str | None = Query(None, description="Free-text / semantic search query"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    clauses: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if title:
        clauses.append("title ILIKE :title")
        params["title"] = f"%{title}%"
    if skill:
        # skills is a JSONB array of {name, weight} objects
        clauses.append("skills::text ILIKE :skill")
        params["skill"] = f"%{skill}%"
    if min_salary is not None:
        clauses.append("salary_min >= :min_salary")
        params["min_salary"] = min_salary
    if remote is not None:
        clauses.append("is_remote = :remote")
        params["remote"] = remote
    if seniority:
        clauses.append("seniority = :seniority")
        params["seniority"] = seniority
    if q:
        # Keyword fallback; swap for pgvector cosine (embedding <=> :vec) once
        # embeddings are populated by the enrichment pipeline.
        clauses.append("(title ILIKE :q OR description ILIKE :q)")
        params["q"] = f"%{q}%"

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    query = f"""
        SELECT id, title, company, location, is_remote, remote_type,
               salary_min, salary_max, salary_currency, posted_at, url, seniority
        FROM jobs
        {where}
        ORDER BY posted_at DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """

    try:
        jobs = _fetch_all(query, params)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc

    return {"count": len(jobs), "limit": limit, "offset": offset, "jobs": jobs}


@app.get("/stats")
def stats() -> dict[str, Any]:
    try:
        total = _fetch_one("SELECT COUNT(*) AS n FROM jobs")
        by_source = _fetch_all(
            "SELECT source, COUNT(*) AS n FROM jobs GROUP BY source ORDER BY n DESC"
        )
        by_seniority = _fetch_all(
            "SELECT seniority, COUNT(*) AS n FROM jobs WHERE seniority IS NOT NULL GROUP BY seniority ORDER BY n DESC"
        )
        salary = _fetch_one(
            """
            SELECT
              COUNT(*) FILTER (WHERE salary_ok) AS above_150k,
              ROUND(AVG(salary_min), 0) AS avg_salary_min,
              ROUND(AVG(salary_max), 0) AS avg_salary_max
            FROM jobs
            """
        )
        remote = _fetch_one(
            "SELECT COUNT(*) FILTER (WHERE is_remote) AS remote_count FROM jobs"
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"database error: {exc}") from exc

    return {
        "total_jobs": total["n"] if total else 0,
        "remote_jobs": remote["remote_count"] if remote else 0,
        "above_150k": salary["above_150k"] if salary else 0,
        "avg_salary_min": salary["avg_salary_min"] if salary else None,
        "avg_salary_max": salary["avg_salary_max"] if salary else None,
        "by_source": by_source,
        "by_seniority": by_seniority,
    }

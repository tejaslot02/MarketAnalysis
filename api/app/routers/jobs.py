"""Jobs listing router with asynchronous database connectivity."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.app.dependencies.db import get_async_engine
from api.app.schemas.job import JobListResponse

router = APIRouter(tags=["Jobs"])


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    title: str | None = Query(None, description="Title substring (e.g. 'machine learning engineer')"),
    skill: str | None = Query(None, description="Required skill (e.g. 'pytorch')"),
    min_salary: int | None = Query(None, ge=0, description="Minimum annual salary in USD"),
    remote: bool | None = Query(None, description="Filter by remote flag"),
    seniority: str | None = Query(None, description="senior|staff|principal|lead|manager|director"),
    q: str | None = Query(None, description="Free-text query"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Retrieve filtered, paginated list of canonical job postings."""
    clauses: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if title:
        clauses.append("title ILIKE :title")
        params["title"] = f"%{title}%"
    if skill:
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
        clauses.append("(title ILIKE :q OR description ILIKE :q)")
        params["q"] = f"%{q}%"

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    query = f"""
        SELECT id, title, company, location, is_remote, remote_type,
               salary_min, salary_max, salary_currency, posted_at, url, seniority,
               skills, responsibilities, description
        FROM jobs
        {where}
        ORDER BY posted_at DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """

    engine = get_async_engine()
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(text(query), params)).mappings().all()
            jobs = [dict(r) for r in rows]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc

    return {"count": len(jobs), "limit": limit, "offset": offset, "jobs": jobs}

"""Market and ETL statistics router."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.app.dependencies.db import get_async_engine
from api.app.schemas.job import StatsResponse

router = APIRouter(tags=["Stats"])


@router.get("/stats", response_model=StatsResponse)
async def stats() -> dict[str, Any]:
    """Retrieve aggregate market indicators and data volume metrics."""
    engine = get_async_engine()
    try:
        async with engine.connect() as conn:
            total_row = (
                await conn.execute(text("SELECT COUNT(*) AS n FROM jobs"))
            ).mappings().first()
            total_n = total_row["n"] if total_row else 0

            by_source_rows = (
                await conn.execute(
                    text("SELECT source, COUNT(*) AS n FROM jobs GROUP BY source ORDER BY n DESC")
                )
            ).mappings().all()
            by_source = [dict(r) for r in by_source_rows]

            by_sen_rows = (
                await conn.execute(
                    text(
                        "SELECT seniority, COUNT(*) AS n FROM jobs WHERE seniority IS NOT NULL GROUP BY seniority ORDER BY n DESC"
                    )
                )
            ).mappings().all()
            by_seniority = [dict(r) for r in by_sen_rows]

            salary_sql = """
                SELECT
                  COUNT(*) FILTER (WHERE salary_ok) AS above_150k,
                  ROUND(AVG(salary_min), 0) AS avg_salary_min,
                  ROUND(AVG(salary_max), 0) AS avg_salary_max
                FROM jobs
            """
            salary_row = (await conn.execute(text(salary_sql))).mappings().first()

            remote_row = (
                await conn.execute(
                    text("SELECT COUNT(*) FILTER (WHERE is_remote) AS remote_count FROM jobs")
                )
            ).mappings().first()

    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc

    return {
        "total_jobs": total_n,
        "remote_jobs": remote_row["remote_count"] if remote_row else 0,
        "above_150k": salary_row["above_150k"] if salary_row else 0,
        "avg_salary_min": salary_row["avg_salary_min"] if salary_row else None,
        "avg_salary_max": salary_row["avg_salary_max"] if salary_row else None,
        "by_source": by_source,
        "by_seniority": by_seniority,
    }

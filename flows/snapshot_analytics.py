"""Prefect flow: write daily analytics snapshots for trend analysis.

Captures headline metrics + per-skill / per-title / per-company / per-source
counts into *_trend tables so demand curves can be plotted over time (e.g.
"Agentic AI" growth, emerging titles, company hiring velocity). Idempotent per
snapshot_date (ON CONFLICT DO UPDATE).

Run ad hoc:  python flows/snapshot_analytics.py
"""
from __future__ import annotations

import asyncio
import os
from datetime import date
from typing import Any

from prefect import flow, get_run_logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/jobs",
)


@flow(name="snapshot-analytics")
async def snapshot_analytics_flow() -> dict[str, int]:
    logger = get_run_logger()
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    today = date.today()
    counts: dict[str, int] = {}

    async with engine.begin() as conn:
        # 1) headline snapshot
        row = (await conn.execute(text("""
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE is_remote) AS remote,
                   COUNT(*) FILTER (WHERE jsonb_array_length(skills) > 0) AS with_skills,
                   COUNT(*) FILTER (WHERE salary_ok) AS above_150k
            FROM jobs
        """))).mappings().first()
        companies = (await conn.execute(text("SELECT COUNT(*) AS n FROM companies"))).scalar() or 0
        await conn.execute(text("""
            INSERT INTO analytics_snapshots
                (snapshot_date, total_jobs, remote_jobs, jobs_with_skills, companies, above_150k)
            VALUES (:d, :total, :remote, :skills, :companies, :above)
            ON CONFLICT (snapshot_date) DO UPDATE SET
                total_jobs = EXCLUDED.total_jobs,
                remote_jobs = EXCLUDED.remote_jobs,
                jobs_with_skills = EXCLUDED.jobs_with_skills,
                companies = EXCLUDED.companies,
                above_150k = EXCLUDED.above_150k
        """), {"d": today, "total": row["total"], "remote": row["remote"],
               "skills": row["with_skills"], "companies": companies, "above": row["above_150k"]})

        # 2) skill trend
        skills = (await conn.execute(text("""
            SELECT s->>'name' AS skill, s->>'category' AS category, COUNT(*) AS n
            FROM jobs, jsonb_array_elements(skills) s GROUP BY 1, 2
        """))).mappings().all()
        for s in skills:
            await conn.execute(text("""
                INSERT INTO skill_trend (snapshot_date, skill, category, job_count)
                VALUES (:d, :skill, :cat, :n)
                ON CONFLICT (snapshot_date, skill) DO UPDATE SET
                    job_count = EXCLUDED.job_count, category = EXCLUDED.category
            """), {"d": today, "skill": s["skill"], "cat": s["category"], "n": s["n"]})
        counts["skills"] = len(skills)

        # 3) title trend
        titles = (await conn.execute(text("""
            SELECT title_canonical, COUNT(*) AS n FROM jobs
            WHERE title_canonical IS NOT NULL GROUP BY 1
        """))).mappings().all()
        for t in titles:
            await conn.execute(text("""
                INSERT INTO title_trend (snapshot_date, title_canonical, job_count)
                VALUES (:d, :title, :n)
                ON CONFLICT (snapshot_date, title_canonical) DO UPDATE SET job_count = EXCLUDED.job_count
            """), {"d": today, "title": t["title_canonical"], "n": t["n"]})
        counts["titles"] = len(titles)

        # 4) company hiring
        comps = (await conn.execute(text("""
            SELECT company, COUNT(*) AS active,
                   COUNT(*) FILTER (WHERE first_seen_at::date = :d) AS new
            FROM jobs WHERE company IS NOT NULL AND company <> '' GROUP BY company
        """), {"d": today})).mappings().all()
        for c in comps:
            await conn.execute(text("""
                INSERT INTO company_hiring (snapshot_date, company, jobs_active, jobs_new)
                VALUES (:d, :company, :active, :new)
                ON CONFLICT (snapshot_date, company) DO UPDATE SET
                    jobs_active = EXCLUDED.jobs_active, jobs_new = EXCLUDED.jobs_new
            """), {"d": today, "company": c["company"], "active": c["active"], "new": c["new"]})
        counts["companies"] = len(comps)

        # 5) source trend
        sources = (await conn.execute(text("SELECT source, COUNT(*) AS n FROM jobs GROUP BY source"))).mappings().all()
        for s in sources:
            await conn.execute(text("""
                INSERT INTO source_trend (snapshot_date, source, job_count)
                VALUES (:d, :source, :n)
                ON CONFLICT (snapshot_date, source) DO UPDATE SET job_count = EXCLUDED.job_count
            """), {"d": today, "source": s["source"], "n": s["n"]})
        counts["sources"] = len(sources)

    await engine.dispose()
    logger.info("Analytics snapshot written for %s: %s", today, counts)
    return counts


if __name__ == "__main__":
    print(asyncio.run(snapshot_analytics_flow()))

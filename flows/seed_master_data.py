"""Prefect flow: seed master-data dimension tables from the YAML dictionaries.

Populates `portals`, `skills`, `job_titles`, and `companies` (idempotent upserts).
Flattening logic lives in dictionaries.py (dependency-light, unit-testable).

Run ad hoc:  python flows/seed_master_data.py
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

from prefect import flow, get_run_logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from dictionaries import (
    flatten_companies,
    flatten_portals,
    flatten_skills,
    flatten_titles,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/jobs",
)

TITLES_UPSERT = text(
    """
    INSERT INTO job_titles (id, canonical, track, synonyms)
    VALUES (:id, :canonical, :track, CAST(:synonyms AS jsonb))
    ON CONFLICT (id) DO UPDATE SET
        canonical = EXCLUDED.canonical,
        track     = EXCLUDED.track,
        synonyms  = EXCLUDED.synonyms
    """
)


async def _upsert(engine, table: str, columns: list[str], rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    cols = ", ".join(columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "id")
    sql = text(f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT (id) DO UPDATE SET {updates}")
    n = 0
    async with engine.begin() as conn:
        for r in rows:
            await conn.execute(sql, {c: r.get(c) for c in columns})
            n += 1
    return n


@flow(name="seed-master-data")
async def seed_master_data_flow() -> dict[str, int]:
    logger = get_run_logger()
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

    skills = flatten_skills()
    portals = flatten_portals()
    titles = flatten_titles()
    companies = flatten_companies()

    counts = {
        "skills": await _upsert(engine, "skills", ["id", "name", "category", "subcategory", "weight"], skills),
        "portals": await _upsert(engine, "portals", ["id", "name", "type", "url", "priority", "scraping_method", "api", "salary_data", "remote_filter"], portals),
        "companies": await _upsert(engine, "companies", ["id", "name", "greenhouse_token", "lever_slug", "ashby_org", "workable_account"], companies),
    }

    # job_titles.synonyms is JSONB -> upsert with an explicit CAST (no generic upsert)
    n_titles = 0
    async with engine.begin() as conn:
        for t in titles:
            await conn.execute(TITLES_UPSERT, {
                "id": t["id"], "canonical": t["canonical"],
                "track": t.get("track"), "synonyms": t.get("synonyms"),
            })
            n_titles += 1
    counts["job_titles"] = n_titles

    await engine.dispose()
    logger.info("Master data seeded: %s", counts)
    return counts


if __name__ == "__main__":
    print(asyncio.run(seed_master_data_flow()))

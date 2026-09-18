"""Prefect flow: seed master-data dimension tables from the YAML dictionaries.

Populates `portals`, `skills`, `job_titles`, and `companies` (idempotent upserts).
This is the "skill database" + master-data layer backing the Metabase dashboard.

Run ad hoc:  python flows/seed_master_data.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

import yaml
from prefect import flow, get_run_logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DICTIONARY_DIR = os.getenv("DICTIONARY_DIR", "/opt/prefect/data/dictionaries")
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


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "unknown"


def _load(name: str) -> Any:
    with open(os.path.join(DICTIONARY_DIR, name), encoding="utf-8") as f:
        return yaml.safe_load(f)


def _flatten_skills() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    skills_map = _load("skills_technologies.yaml").get("skills", {})
    for category, entries in skills_map.items():
        if category == "domain_specializations":
            for sub, sub_entries in entries.items():
                for e in sub_entries:
                    out.append({
                        "id": _slug(e["name"]),
                        "name": e["name"],
                        "category": category,
                        "subcategory": sub,
                        "weight": e.get("weight", 5),
                    })
        else:
            for e in entries:
                out.append({
                    "id": _slug(e["name"]),
                    "name": e["name"],
                    "category": category,
                    "subcategory": None,
                    "weight": e.get("weight", 5),
                })
    return out


def _flatten_portals() -> list[dict[str, Any]]:
    out = []
    for p in _load("job_portals.yaml").get("portals", []):
        api = p.get("api")
        if isinstance(api, bool):
            api = "yes" if api else "no"  # PyYAML coerces unquoted yes/no -> bool
        out.append({
            "id": _slug(p["name"]),
            "name": p["name"],
            "type": p.get("type"),
            "url": p.get("url"),
            "priority": p.get("priority"),
            "scraping_method": p.get("scraping_method"),
            "api": api,
            "salary_data": bool(p.get("salary_data")),
            "remote_filter": bool(p.get("remote_filter")),
        })
    return out


def _flatten_titles() -> list[dict[str, Any]]:
    out = []
    for t in _load("job_titles.yaml").get("titles", []):
        out.append({
            "id": _slug(t["canonical"]),
            "canonical": t["canonical"],
            "track": t.get("track"),
            "synonyms": json.dumps(t.get("synonyms", [])),
        })
    return out


def _flatten_companies() -> list[dict[str, Any]]:
    ats = _load("companies.yaml").get("ats", {}) or {}
    field_map = {
        "greenhouse": "greenhouse_token",
        "lever": "lever_slug",
        "ashby": "ashby_org",
        "workable": "workable_account",
    }
    merged: dict[str, dict[str, Any]] = {}
    for spider, handles in ats.items():
        col = field_map.get(spider)
        if not col:
            continue
        for h in handles or []:
            slug = _slug(h)
            rec = merged.setdefault(slug, {
                "id": slug, "name": h,
                "greenhouse_token": None, "lever_slug": None,
                "ashby_org": None, "workable_account": None,
            })
            rec[col] = h
    return list(merged.values())


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

    skills = _flatten_skills()
    portals = _flatten_portals()
    titles = _flatten_titles()
    companies = _flatten_companies()

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

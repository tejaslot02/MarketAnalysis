"""Prefect flow: run all configured portal spiders (the Extract stage).

Each spider emits normalized records to the Dragonfly stream `raw-jobs` via the
Scrapy item pipeline (scrapers/pipelines.py). The `consume-raw-jobs` flow then
drains the stream into Postgres / Elasticsearch / MinIO.

Fan-out: ATS spiders (greenhouse/lever/ashby/workable) run once per company
listed in data/dictionaries/companies.yaml; standalone boards run once each.
Every run is recorded in the `portal_runs` table for freshness monitoring.

Run ad hoc:  python flows/scrape_portals.py
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import time
from typing import Any

import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from prefect import flow, get_run_logger

SCRAPERS_DIR = os.getenv("SCRAPERS_DIR", "/opt/prefect/scrapers")
DICTIONARY_DIR = os.getenv("DICTIONARY_DIR", "/opt/prefect/data/dictionaries")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/jobs",
)

# (spider_name, default_args). ATS spiders are appended from companies.yaml.
STANDALONE_SPIDERS: list[tuple[str, dict[str, str]]] = [
    ("remotive", {}),
    ("weworkremotely", {}),
    ("remoteok", {}),
    ("jobicy", {}),
    ("arbeitnow", {}),
    ("himalayas", {}),
    ("workingnomads", {}),
    ("aijobs", {}),
    ("builtin", {}),
]

# ATS spider name -> the `-a` argument key that carries the board handle.
ATS_ARG_KEY = {
    "greenhouse": "board_token",
    "lever": "company",
    "ashby": "org",
    "workable": "account",
}

RUN_INSERT_SQL = text(
    """
    INSERT INTO portal_runs (portal, started_at, finished_at, status, jobs_emitted, error)
    VALUES (:portal, to_timestamp(:started), to_timestamp(:finished), :status, :jobs, :error)
    """
)


def _load_companies() -> dict[str, Any]:
    path = os.path.join(DICTIONARY_DIR, "companies.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _spider_tasks(selected: list[str] | None = None) -> list[tuple[str, dict[str, str]]]:
    tasks: list[tuple[str, dict[str, str]]] = list(STANDALONE_SPIDERS)
    ats = _load_companies().get("ats", {}) or {}
    for spider, key in ATS_ARG_KEY.items():
        for handle in ats.get(spider, []) or []:
            tasks.append((spider, {key: str(handle)}))
    if selected:
        tasks = [t for t in tasks if t[0] in selected]
    return tasks


def _run_spider(name: str, args: dict[str, str]) -> tuple[int, str, str]:
    cmd = ["scrapy", "crawl", name]
    for k, v in args.items():
        cmd += ["-a", f"{k}={v}"]
    proc = subprocess.run(
        cmd, cwd=SCRAPERS_DIR, capture_output=True, text=True, timeout=1200,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


async def _persist_runs(engine, results: list[dict[str, Any]]) -> None:
    if not results:
        return
    async with engine.begin() as conn:
        for r in results:
            await conn.execute(
                RUN_INSERT_SQL,
                {
                    "portal": r["portal"],
                    "started": r["started"],
                    "finished": r["finished"],
                    "status": r["status"],
                    "jobs": r["jobs"],
                    "error": (r.get("error") or "")[:2000],
                },
            )


@flow(name="scrape-portals")
async def scrape_portals_flow(selected_spiders: list[str] | None = None) -> list[dict[str, Any]]:
    logger = get_run_logger()
    tasks = _spider_tasks(selected_spiders)
    logger.info("Scraping %d spider tasks from %s", len(tasks), SCRAPERS_DIR)

    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    results: list[dict[str, Any]] = []
    for name, args in tasks:
        started = time.time()
        logger.info("Running spider %s args=%s", name, args)
        try:
            rc, out, err = await asyncio.to_thread(_run_spider, name, args)
        except Exception as exc:  # noqa: BLE001
            rc, out, err = -1, "", str(exc)
        jobs = ((out or "") + (err or "")).count("XADD")  # Scrapy logs to stderr
        status = "success" if rc == 0 else "error"
        result = {
            "portal": name,
            "started": started,
            "finished": time.time(),
            "status": status,
            "jobs": jobs,
            "error": err or None,
        }
        results.append(result)
        await _persist_runs(engine, [result])  # live observability: write per-spider
        logger.info("[%s] %s args=%s jobs=%d (%.1fs)", status, name, args, jobs, time.time() - started)
        if rc != 0:
            logger.error("stderr tail: %s", (err or "")[-1000:])

    # Note: spider results are already persisted per-spider above to support live observability.
    await engine.dispose()
    return results



if __name__ == "__main__":
    import sys
    selected = sys.argv[1:] if len(sys.argv) > 1 else None
    asyncio.run(scrape_portals_flow(selected))

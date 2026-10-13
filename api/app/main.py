"""Enterprise FastAPI serving application for Remote 150K+ DS/AI/ML Job Search Platform.

Modular Monolith architecture delegating endpoints to specialized routers:
  - api/app/routers/health.py  (/health)
  - api/app/routers/jobs.py    (/jobs)
  - api/app/routers/stats.py   (/stats)
  - api/app/routers/search.py  (/search - Hybrid Vector + BM25)
"""
from __future__ import annotations

from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Gauge,
    generate_latest,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.app.dependencies.cache import get_redis_client
from api.app.dependencies.db import get_async_engine
from api.app.routers.health import router as health_router
from api.app.routers.jobs import router as jobs_router
from api.app.routers.search import router as search_router
from api.app.routers.stats import router as stats_router
from config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise Job Search & Analytics Serving Platform",
)

# Register modular routers
app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(stats_router)
app.include_router(search_router)


@app.get("/metrics", tags=["Observability"])
async def metrics() -> Response:
    """Prometheus metrics endpoint for ETL observability and system health."""
    registry = CollectorRegistry()

    jobs_by_source = Gauge(
        "etl_jobs_total", "Total canonical jobs by source", ["source"], registry=registry
    )
    jobs_with_skills = Gauge(
        "etl_jobs_with_skills_total",
        "Jobs with at least one extracted skill",
        registry=registry,
    )
    companies = Gauge(
        "etl_companies_total", "Companies in master data", registry=registry
    )
    portal_runs = Gauge(
        "etl_portal_runs_total",
        "Portal scrape runs by portal and status",
        ["portal", "status"],
        registry=registry,
    )
    portal_last_success = Gauge(
        "etl_portal_last_success_timestamp_seconds",
        "Last successful portal run (unix seconds)",
        ["portal"],
        registry=registry,
    )
    stream_backlog = Gauge(
        "etl_stream_backlog", "Raw-jobs stream backlog (XLEN)", registry=registry
    )
    stream_pending = Gauge(
        "etl_stream_pending",
        "Raw-jobs stream pending messages (XPENDING)",
        registry=registry,
    )
    dlq_depth = Gauge(
        "etl_dlq_depth",
        "Dead-letter queue backlog length",
        registry=registry,
    )

    engine = get_async_engine()
    try:
        async with engine.connect() as conn:
            for row in (
                await conn.execute(
                    text("SELECT source, COUNT(*) AS n FROM jobs GROUP BY source")
                )
            ).mappings():
                jobs_by_source.labels(source=row["source"]).set(row["n"])

            skills_count = (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM jobs WHERE jsonb_array_length(skills) > 0"
                    )
                )
            ).scalar()
            jobs_with_skills.set(skills_count or 0)

            companies_count = (
                await conn.execute(text("SELECT COUNT(*) FROM companies"))
            ).scalar()
            companies.set(companies_count or 0)

            for row in (
                await conn.execute(
                    text(
                        "SELECT portal, status, COUNT(*) AS n FROM portal_runs GROUP BY 1, 2"
                    )
                )
            ).mappings():
                portal_runs.labels(portal=row["portal"], status=row["status"]).set(
                    row["n"]
                )

            for row in (
                await conn.execute(
                    text(
                        "SELECT portal, MAX(finished_at) AS t FROM portal_runs WHERE status = 'success' GROUP BY 1"
                    )
                )
            ).mappings():
                if row["t"] is not None:
                    portal_last_success.labels(portal=row["portal"]).set(
                        row["t"].timestamp()
                    )
    except SQLAlchemyError:
        pass

    try:
        r = get_redis_client()
        stream_backlog.set(int(r.xlen(settings.stream_name) or 0))
        p = r.xpending(settings.stream_name, settings.stream_group)
        if isinstance(p, dict) and "pending" in p:
            stream_pending.set(int(p["pending"]))
        dlq_depth.set(int(r.xlen(settings.dlq_stream_name) or 0))
        r.close()
    except Exception:
        pass

    return Response(
        content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST
    )

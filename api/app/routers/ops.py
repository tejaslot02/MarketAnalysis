"""Data Operations & Pipeline Management router for the Ops Control Plane."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
import logging
import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
import httpx
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.app.dependencies.cache import get_redis_client
from api.app.dependencies.db import get_async_engine
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/ops", tags=["Operations"])

pipeline_state: dict[str, Any] = {
    "is_running": False,
    "current_stage": "idle",
    "stage_index": 0,
    "started_at": None,
    "finished_at": None,
    "last_status": "idle",
    "last_error": None,
}


class TriggerPipelineRequest(BaseModel):
    mode: str = "quick"  # "quick" | "full" | "etl"


class ReplayRequest(BaseModel):
    count: int = 100
    target_stream: str = "raw-jobs"


class PromoteSkillRequest(BaseModel):
    term: str
    category: str = "domain_specializations"
    weight: int = 5


@router.get("/stream-status")
def get_stream_status() -> dict[str, Any]:
    """Retrieve real-time message queue status, stream backpressure, and DLQ depth."""
    try:
        r = get_redis_client()
        stream_len = int(r.xlen(settings.stream_name) or 0)
        dlq_len = int(r.xlen(settings.dlq_stream_name) or 0)

        pending_count = 0
        lag_count = 0
        entries_read = 0

        try:
            p = r.xpending(settings.stream_name, settings.stream_group)
            if isinstance(p, dict) and "pending" in p:
                pending_count = int(p["pending"])
        except Exception:
            pass

        try:
            groups = r.xinfo_groups(settings.stream_name)
            for g in groups:
                if g.get("name") == settings.stream_group:
                    lag_count = int(g.get("lag", 0) or 0)
                    entries_read = int(g.get("entries-read", 0) or 0)
                    break
        except Exception:
            pass

        r.close()
        return {
            "status": "connected",
            "stream_name": settings.stream_name,
            "stream_group": settings.stream_group,
            "stream_buffer_total": stream_len,
            "stream_backlog": lag_count,
            "stream_pending": pending_count,
            "entries_read": entries_read,
            "dlq_stream_name": settings.dlq_stream_name,
            "dlq_depth": dlq_len,
            "stream_max_capacity": settings.stream_maxlen,
            "fill_percentage": round((stream_len / max(settings.stream_maxlen, 1)) * 100, 2),
        }
    except Exception as exc:
        logger.warning("Redis stream status check degraded: %s", exc)
        return {
            "status": "degraded",
            "stream_name": settings.stream_name,
            "stream_backlog": 0,
            "stream_pending": 0,
            "dlq_depth": 0,
            "error": str(exc),
        }


@router.get("/dlq-messages")
def list_dlq_messages(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    """Retrieve the most recent poisoned messages routed to the Dead-Letter Queue."""
    try:
        r = get_redis_client()
        messages = r.xrevrange(settings.dlq_stream_name, count=limit)
        items = []
        for mid, fields in messages:
            payload_str = fields.get("payload", "{}")
            parsed_payload: Any = payload_str
            try:
                parsed_payload = json.loads(payload_str)
            except Exception:
                pass

            items.append({
                "dlq_id": mid,
                "original_id": fields.get("original_id", "unknown"),
                "failed_at": fields.get("failed_at"),
                "error_type": fields.get("error_type", "UnknownError"),
                "error_message": fields.get("error_message", ""),
                "payload": parsed_payload,
            })
        r.close()
        return {"count": len(items), "messages": items}
    except Exception as exc:
        logger.warning("Error reading DLQ messages: %s", exc)
        return {"count": 0, "messages": [], "error": str(exc)}


@router.post("/dlq-replay")
def replay_dlq_messages(body: ReplayRequest) -> dict[str, Any]:
    """Re-drive poisoned messages from raw-jobs-dlq back into the primary raw-jobs stream."""
    try:
        r = get_redis_client()
        try:
            from flows.dlq_handler import replay_dlq
            replayed = replay_dlq(r, target_stream=body.target_stream, count=body.count)
        except (ImportError, ModuleNotFoundError):
            # Fallback manual replay if flows not in pythonpath
            messages = r.xrange(settings.dlq_stream_name, count=body.count)
            replayed = 0
            for mid, fields in messages:
                payload = fields.get("payload", "{}")
                r.xadd(body.target_stream, {"data": payload}, maxlen=100000, approximate=True)
                r.xdel(settings.dlq_stream_name, mid)
                replayed += 1

        remaining = int(r.xlen(settings.dlq_stream_name) or 0)
        r.close()
        return {
            "replayed": replayed,
            "remaining_dlq": remaining,
            "target_stream": body.target_stream,
            "status": "success",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to replay DLQ: {exc}") from exc


@router.get("/spider-runs")
async def get_spider_runs(limit: int = Query(25, ge=1, le=100)) -> dict[str, Any]:
    """Retrieve execution history, durations, and health statuses of web crawlers."""
    engine = get_async_engine()
    sql = """
        SELECT id, portal, started_at, finished_at, status, jobs_emitted, error,
               ROUND(EXTRACT(EPOCH FROM (finished_at - started_at))::numeric, 1) AS duration_seconds
        FROM portal_runs
        ORDER BY started_at DESC
        LIMIT :limit
    """
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(text(sql), {"limit": limit})).mappings().all()
            runs = [dict(r) for r in rows]
            return {"count": len(runs), "runs": runs}
    except SQLAlchemyError as exc:
        logger.warning("Could not fetch portal_runs: %s", exc)
        return {"count": 0, "runs": [], "error": str(exc)}


@router.get("/taxonomy-candidates")
async def get_taxonomy_candidates(limit: int = Query(30, ge=1, le=100)) -> dict[str, Any]:
    """Retrieve newly discovered technical skill candidates mined from descriptions."""
    engine = get_async_engine()
    sql = """
        SELECT term, frequency, sample_contexts
        FROM new_skill_candidates
        ORDER BY frequency DESC
        LIMIT :limit
    """
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(text(sql), {"limit": limit})).mappings().all()
            candidates = [dict(r) for r in rows]
            return {"count": len(candidates), "candidates": candidates}
    except SQLAlchemyError as exc:
        logger.warning("Could not fetch new_skill_candidates: %s", exc)
        return {"count": 0, "candidates": [], "error": str(exc)}


@router.post("/promote-skill")
async def promote_skill_candidate(body: PromoteSkillRequest) -> dict[str, Any]:
    """Promote a discovered candidate term into the master skills table."""
    engine = get_async_engine()
    slug = body.term.strip().lower().replace(" ", "_")
    sql = """
        INSERT INTO skills (id, name, category, weight)
        VALUES (:id, :name, :category, :weight)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            category = EXCLUDED.category,
            weight = EXCLUDED.weight
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(sql),
                {
                    "id": slug,
                    "name": body.term.strip(),
                    "category": body.category,
                    "weight": body.weight,
                },
            )
            # Remove candidate from skill_candidates after promotion
            await conn.execute(
                text("DELETE FROM skill_candidates WHERE lower(term) = lower(:term)"),
                {"term": body.term.strip()},
            )
        return {"status": "promoted", "skill_id": slug, "term": body.term}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error promoting skill: {exc}") from exc


async def _wait_for_flow_run(client: httpx.AsyncClient, prefect_url: str, flow_run_id: str, max_seconds: int = 300) -> str:
    elapsed = 0
    while elapsed < max_seconds:
        try:
            r = await client.get(f"{prefect_url}/flow_runs/{flow_run_id}")
            if r.status_code == 200:
                state_name = (r.json().get("state_name") or "").upper()
                if state_name in ("COMPLETED", "FAILED", "CRASHED", "CANCELLED"):
                    return state_name
        except Exception:
            pass
        await asyncio.sleep(2)
        elapsed += 2
    return "TIMEOUT"


async def _run_pipeline_background(mode: str) -> None:
    global pipeline_state
    pipeline_state["is_running"] = True
    pipeline_state["started_at"] = datetime.now(UTC).isoformat()
    pipeline_state["last_status"] = "running"
    pipeline_state["last_error"] = None

    prefect_url = os.getenv("PREFECT_API_URL", "http://prefect-server:4200/api")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            deps_resp = await client.post(f"{prefect_url}/deployments/filter", json={})
            if deps_resp.status_code != 200:
                raise RuntimeError(f"Prefect server unreachable (HTTP {deps_resp.status_code})")

            deps = {d["name"]: d["id"] for d in deps_resp.json()}

            # 1. Seed master data
            if "seed-master-data" in deps:
                pipeline_state["current_stage"] = "Seeding master dimensions"
                pipeline_state["stage_index"] = 1
                r = await client.post(f"{prefect_url}/deployments/{deps['seed-master-data']}/create_flow_run", json={})
                if r.status_code in (200, 201):
                    await _wait_for_flow_run(client, prefect_url, r.json()["id"], max_seconds=60)

            # 2. Extract Stage: Web Spiders
            if mode != "etl" and "scrape-portals-daily" in deps:
                pipeline_state["current_stage"] = "Crawling live job portals (Extract)"
                pipeline_state["stage_index"] = 2
                params = {"selected_spiders": ["remotive", "arbeitnow"]} if mode == "quick" else {}
                r = await client.post(
                    f"{prefect_url}/deployments/{deps['scrape-portals-daily']}/create_flow_run",
                    json={"parameters": params},
                )
                if r.status_code in (200, 201):
                    await _wait_for_flow_run(client, prefect_url, r.json()["id"], max_seconds=300)

            # 3. Transform & Load: Consume Redis Stream
            if "consume-raw-jobs" in deps:
                pipeline_state["current_stage"] = "Stream ingestion & multi-store load"
                pipeline_state["stage_index"] = 3
                r = await client.post(f"{prefect_url}/deployments/{deps['consume-raw-jobs']}/create_flow_run", json={})
                if r.status_code in (200, 201):
                    await _wait_for_flow_run(client, prefect_url, r.json()["id"], max_seconds=300)

            # 4. Analytics & Skills
            if "mine-skills" in deps:
                pipeline_state["current_stage"] = "Mining skill trends & generating snapshots"
                pipeline_state["stage_index"] = 4
                r = await client.post(f"{prefect_url}/deployments/{deps['mine-skills']}/create_flow_run", json={})
                if r.status_code in (200, 201):
                    await _wait_for_flow_run(client, prefect_url, r.json()["id"], max_seconds=120)

            if "snapshot-analytics" in deps:
                await client.post(f"{prefect_url}/deployments/{deps['snapshot-analytics']}/create_flow_run", json={})

        pipeline_state["last_status"] = "success"
        pipeline_state["current_stage"] = "Pipeline completed successfully"
        pipeline_state["stage_index"] = 5
    except Exception as exc:
        logger.error("Pipeline background execution failed: %s", exc)
        pipeline_state["last_status"] = "error"
        pipeline_state["last_error"] = str(exc)
        pipeline_state["current_stage"] = f"Failed: {exc}"
    finally:
        pipeline_state["is_running"] = False
        pipeline_state["finished_at"] = datetime.now(UTC).isoformat()


@router.post("/trigger-pipeline")
async def trigger_pipeline(
    body: TriggerPipelineRequest = TriggerPipelineRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> dict[str, Any]:
    """Trigger end-to-end ingestion and ETL pipeline execution asynchronously from the UI."""
    global pipeline_state
    if pipeline_state.get("is_running"):
        return {
            "status": "already_running",
            "message": "A pipeline run is currently in progress.",
            "current_stage": pipeline_state.get("current_stage"),
            "stage_index": pipeline_state.get("stage_index"),
        }

    background_tasks.add_task(_run_pipeline_background, body.mode)
    return {
        "status": "triggered",
        "mode": body.mode,
        "message": f"Pipeline execution ({body.mode} mode) dispatched to Prefect Orchestrator.",
    }


@router.get("/pipeline-status")
def get_pipeline_status() -> dict[str, Any]:
    """Retrieve active and recent pipeline execution status for UI telemetry."""
    return dict(pipeline_state)


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

MAX_LOG_ENTRIES = 2000
pipeline_logs: list[dict[str, Any]] = []


def _default_stages() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "key": "seed-master-data",
            "name": "Seed Master Dimensions",
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "duration_seconds": None,
            "flow_run_id": None,
            "summary": "Skills, portals, and company dimensions",
        },
        {
            "id": 2,
            "key": "scrape-portals-daily",
            "name": "Crawling Live Job Portals (Extract)",
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "duration_seconds": None,
            "flow_run_id": None,
            "summary": "14 Spiders pushing raw job postings to Redis stream",
        },
        {
            "id": 3,
            "key": "consume-raw-jobs",
            "name": "Stream Ingestion & Multi-Store Load",
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "duration_seconds": None,
            "flow_run_id": None,
            "summary": "Transform, deduplicate & sync to Postgres, ES, MinIO",
        },
        {
            "id": 4,
            "key": "mine-skills",
            "name": "Mining Skill Trends & Snapshots",
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "duration_seconds": None,
            "flow_run_id": None,
            "summary": "Technical skill taxonomy mining and daily analytics snapshot",
        },
    ]


pipeline_state: dict[str, Any] = {
    "is_running": False,
    "mode": "quick",
    "current_stage": "idle",
    "stage_index": 0,
    "total_stages": 4,
    "progress_percent": 0,
    "started_at": None,
    "finished_at": None,
    "duration_seconds": None,
    "last_status": "idle",
    "last_error": None,
    "active_flow_run_id": None,
    "prefect_ui_url": "http://localhost:4200",
    "stages": _default_stages(),
}


def append_pipeline_log(
    message: str,
    level: str = "INFO",
    source: str = "orchestrator",
    flow_run_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    global pipeline_logs
    if not timestamp:
        timestamp = datetime.now(UTC).isoformat()
    entry = {
        "id": f"log-{len(pipeline_logs) + 1}",
        "timestamp": timestamp,
        "level": level.upper(),
        "source": source,
        "flow_run_id": flow_run_id,
        "message": message,
    }
    pipeline_logs.append(entry)
    if len(pipeline_logs) > MAX_LOG_ENTRIES:
        pipeline_logs.pop(0)
    return entry


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


async def _fetch_flow_run_logs(
    client: httpx.AsyncClient,
    prefect_url: str,
    flow_run_id: str,
    flow_name: str,
    seen_log_ids: set[str],
) -> None:
    try:
        r = await client.post(
            f"{prefect_url}/logs/filter",
            json={
                "logs": {"flow_run_id": {"any_": [flow_run_id]}},
                "sort": "TIMESTAMP_ASC",
                "limit": 250,
            },
        )
        if r.status_code == 200:
            for log in r.json():
                lid = log.get("id")
                if lid and lid not in seen_log_ids:
                    seen_log_ids.add(lid)
                    lvl_num = log.get("level", 20)
                    lvl_str = "INFO"
                    if lvl_num >= 40:
                        lvl_str = "ERROR"
                    elif lvl_num >= 30:
                        lvl_str = "WARN"
                    elif lvl_num <= 10:
                        lvl_str = "DEBUG"

                    msg = log.get("message", "")
                    if "[success]" in msg.lower():
                        lvl_str = "SUCCESS"

                    append_pipeline_log(
                        message=msg,
                        level=lvl_str,
                        source=flow_name,
                        flow_run_id=flow_run_id,
                        timestamp=log.get("timestamp"),
                    )
    except Exception as exc:
        logger.debug("Prefect log stream fetch failed: %s", exc)


async def _wait_for_flow_run(
    client: httpx.AsyncClient,
    prefect_url: str,
    flow_run_id: str,
    flow_name: str,
    max_seconds: int = 300,
) -> str:
    elapsed = 0
    seen_log_ids: set[str] = set()
    while elapsed < max_seconds:
        await _fetch_flow_run_logs(client, prefect_url, flow_run_id, flow_name, seen_log_ids)
        try:
            r = await client.get(f"{prefect_url}/flow_runs/{flow_run_id}")
            if r.status_code == 200:
                state_name = (r.json().get("state_name") or "").upper()
                if state_name in ("COMPLETED", "FAILED", "CRASHED", "CANCELLED"):
                    await asyncio.sleep(0.5)
                    await _fetch_flow_run_logs(client, prefect_url, flow_run_id, flow_name, seen_log_ids)
                    return state_name
        except Exception:
            pass
        await asyncio.sleep(2)
        elapsed += 2
    return "TIMEOUT"


async def _run_pipeline_background(mode: str) -> None:
    global pipeline_state, pipeline_logs
    start_dt = datetime.now(UTC)
    pipeline_state["is_running"] = True
    pipeline_state["mode"] = mode
    pipeline_state["started_at"] = start_dt.isoformat()
    pipeline_state["finished_at"] = None
    pipeline_state["duration_seconds"] = None
    pipeline_state["last_status"] = "running"
    pipeline_state["last_error"] = None
    pipeline_state["progress_percent"] = 5
    pipeline_state["stages"] = _default_stages()

    append_pipeline_log(
        f"=== Pipeline execution dispatched in '{mode.upper()}' mode ===",
        level="INFO",
        source="orchestrator",
    )

    prefect_url = os.getenv("PREFECT_API_URL", "http://prefect-server:4200/api")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            deps_resp = await client.post(f"{prefect_url}/deployments/filter", json={})
            if deps_resp.status_code != 200:
                raise RuntimeError(f"Prefect server unreachable (HTTP {deps_resp.status_code})")

            deps = {d["name"]: d["id"] for d in deps_resp.json()}
            append_pipeline_log(
                f"Discovered {len(deps)} Prefect deployments: {', '.join(deps.keys())}",
                level="INFO",
                source="orchestrator",
            )

            # -----------------------------------------------------------
            # Stage 1: Seed master data
            # -----------------------------------------------------------
            if "seed-master-data" in deps:
                st1_start = datetime.now(UTC)
                pipeline_state["current_stage"] = "Seeding master dimensions"
                pipeline_state["stage_index"] = 1
                pipeline_state["progress_percent"] = 15
                stage_obj = pipeline_state["stages"][0]
                stage_obj["status"] = "running"
                stage_obj["started_at"] = st1_start.isoformat()

                append_pipeline_log(
                    "[Stage 1/4] Triggering seed-master-data flow...",
                    level="INFO",
                    source="seed-master-data",
                )
                r = await client.post(f"{prefect_url}/deployments/{deps['seed-master-data']}/create_flow_run", json={})
                if r.status_code in (200, 201):
                    flow_id = r.json()["id"]
                    stage_obj["flow_run_id"] = flow_id
                    pipeline_state["active_flow_run_id"] = flow_id
                    append_pipeline_log(
                        f"[Stage 1/4] Flow run created: {flow_id}",
                        level="INFO",
                        source="seed-master-data",
                        flow_run_id=flow_id,
                    )
                    state_res = await _wait_for_flow_run(client, prefect_url, flow_id, "seed-master-data", max_seconds=60)
                    st1_dur = round((datetime.now(UTC) - st1_start).total_seconds(), 1)
                    stage_obj["status"] = "completed" if state_res == "COMPLETED" else "failed"
                    stage_obj["finished_at"] = datetime.now(UTC).isoformat()
                    stage_obj["duration_seconds"] = st1_dur
                    append_pipeline_log(
                        f"[Stage 1/4] Seed master data finished ({state_res}) in {st1_dur}s",
                        level="SUCCESS" if state_res == "COMPLETED" else "WARN",
                        source="seed-master-data",
                        flow_run_id=flow_id,
                    )
            else:
                pipeline_state["stages"][0]["status"] = "skipped"

            # -----------------------------------------------------------
            # Stage 2: Extract Stage (Web Spiders)
            # -----------------------------------------------------------
            if mode != "etl" and "scrape-portals-daily" in deps:
                st2_start = datetime.now(UTC)
                pipeline_state["current_stage"] = "Crawling live job portals (Extract)"
                pipeline_state["stage_index"] = 2
                pipeline_state["progress_percent"] = 35
                stage_obj = pipeline_state["stages"][1]
                stage_obj["status"] = "running"
                stage_obj["started_at"] = st2_start.isoformat()

                params = {"selected_spiders": ["remotive", "arbeitnow"]} if mode == "quick" else {}
                spider_label = "2 quick spiders" if mode == "quick" else "all 14 active spiders"
                append_pipeline_log(
                    f"[Stage 2/4] Triggering scrape-portals-daily flow ({spider_label})...",
                    level="INFO",
                    source="scrape-portals",
                )
                r = await client.post(
                    f"{prefect_url}/deployments/{deps['scrape-portals-daily']}/create_flow_run",
                    json={"parameters": params},
                )
                if r.status_code in (200, 201):
                    flow_id = r.json()["id"]
                    stage_obj["flow_run_id"] = flow_id
                    pipeline_state["active_flow_run_id"] = flow_id
                    append_pipeline_log(
                        f"[Stage 2/4] Flow run created: {flow_id}. Crawling live career sites into raw-jobs stream...",
                        level="INFO",
                        source="scrape-portals",
                        flow_run_id=flow_id,
                    )
                    state_res = await _wait_for_flow_run(client, prefect_url, flow_id, "scrape-portals", max_seconds=420)
                    st2_dur = round((datetime.now(UTC) - st2_start).total_seconds(), 1)
                    stage_obj["status"] = "completed" if state_res == "COMPLETED" else "failed"
                    stage_obj["finished_at"] = datetime.now(UTC).isoformat()
                    stage_obj["duration_seconds"] = st2_dur
                    append_pipeline_log(
                        f"[Stage 2/4] Web spider crawls finished ({state_res}) in {st2_dur}s",
                        level="SUCCESS" if state_res == "COMPLETED" else "WARN",
                        source="scrape-portals",
                        flow_run_id=flow_id,
                    )
            else:
                pipeline_state["stages"][1]["status"] = "skipped"

            # -----------------------------------------------------------
            # Stage 3: Transform & Load (Consume Dragonfly Stream)
            # -----------------------------------------------------------
            if "consume-raw-jobs" in deps:
                st3_start = datetime.now(UTC)
                pipeline_state["current_stage"] = "Stream ingestion & multi-store load"
                pipeline_state["stage_index"] = 3
                pipeline_state["progress_percent"] = 65
                stage_obj = pipeline_state["stages"][2]
                stage_obj["status"] = "running"
                stage_obj["started_at"] = st3_start.isoformat()

                append_pipeline_log(
                    "[Stage 3/4] Triggering consume-raw-jobs flow (Dragonfly -> Postgres, ES, MinIO)...",
                    level="INFO",
                    source="consume-raw-jobs",
                )
                r = await client.post(f"{prefect_url}/deployments/{deps['consume-raw-jobs']}/create_flow_run", json={})
                if r.status_code in (200, 201):
                    flow_id = r.json()["id"]
                    stage_obj["flow_run_id"] = flow_id
                    pipeline_state["active_flow_run_id"] = flow_id
                    append_pipeline_log(
                        f"[Stage 3/4] Flow run created: {flow_id}",
                        level="INFO",
                        source="consume-raw-jobs",
                        flow_run_id=flow_id,
                    )
                    state_res = await _wait_for_flow_run(client, prefect_url, flow_id, "consume-raw-jobs", max_seconds=360)
                    st3_dur = round((datetime.now(UTC) - st3_start).total_seconds(), 1)
                    stage_obj["status"] = "completed" if state_res == "COMPLETED" else "failed"
                    stage_obj["finished_at"] = datetime.now(UTC).isoformat()
                    stage_obj["duration_seconds"] = st3_dur
                    append_pipeline_log(
                        f"[Stage 3/4] Stream ingestion finished ({state_res}) in {st3_dur}s",
                        level="SUCCESS" if state_res == "COMPLETED" else "WARN",
                        source="consume-raw-jobs",
                        flow_run_id=flow_id,
                    )
            else:
                pipeline_state["stages"][2]["status"] = "skipped"

            # -----------------------------------------------------------
            # Stage 4: Analytics & Skill Mining
            # -----------------------------------------------------------
            if "mine-skills" in deps:
                st4_start = datetime.now(UTC)
                pipeline_state["current_stage"] = "Mining skill trends & generating snapshots"
                pipeline_state["stage_index"] = 4
                pipeline_state["progress_percent"] = 85
                stage_obj = pipeline_state["stages"][3]
                stage_obj["status"] = "running"
                stage_obj["started_at"] = st4_start.isoformat()

                append_pipeline_log(
                    "[Stage 4/4] Triggering mine-skills flow (Taxonomy candidate extraction)...",
                    level="INFO",
                    source="mine-skills",
                )
                r = await client.post(f"{prefect_url}/deployments/{deps['mine-skills']}/create_flow_run", json={})
                if r.status_code in (200, 201):
                    flow_id = r.json()["id"]
                    stage_obj["flow_run_id"] = flow_id
                    pipeline_state["active_flow_run_id"] = flow_id
                    state_res = await _wait_for_flow_run(client, prefect_url, flow_id, "mine-skills", max_seconds=120)
                    st4_dur = round((datetime.now(UTC) - st4_start).total_seconds(), 1)
                    stage_obj["status"] = "completed" if state_res == "COMPLETED" else "failed"
                    stage_obj["finished_at"] = datetime.now(UTC).isoformat()
                    stage_obj["duration_seconds"] = st4_dur
                    append_pipeline_log(
                        f"[Stage 4/4] Mine skills completed ({state_res}) in {st4_dur}s",
                        level="SUCCESS" if state_res == "COMPLETED" else "WARN",
                        source="mine-skills",
                        flow_run_id=flow_id,
                    )

            if "snapshot-analytics" in deps:
                append_pipeline_log(
                    "Triggering snapshot-analytics flow...",
                    level="INFO",
                    source="snapshot-analytics",
                )
                r = await client.post(f"{prefect_url}/deployments/{deps['snapshot-analytics']}/create_flow_run", json={})
                if r.status_code in (200, 201):
                    flow_id = r.json()["id"]
                    await _wait_for_flow_run(client, prefect_url, flow_id, "snapshot-analytics", max_seconds=60)
                    append_pipeline_log(
                        "Daily analytics snapshot saved to PostgreSQL & MinIO data lake.",
                        level="SUCCESS",
                        source="snapshot-analytics",
                    )

        pipeline_state["last_status"] = "success"
        pipeline_state["current_stage"] = "Pipeline completed successfully"
        pipeline_state["stage_index"] = 4
        pipeline_state["progress_percent"] = 100
        append_pipeline_log(
            "✓ End-to-end data pipeline completed successfully. All data stores synchronized.",
            level="SUCCESS",
            source="orchestrator",
        )
    except Exception as exc:
        logger.error("Pipeline background execution failed: %s", exc)
        pipeline_state["last_status"] = "error"
        pipeline_state["last_error"] = str(exc)
        pipeline_state["current_stage"] = f"Failed: {exc}"
        append_pipeline_log(
            f"Pipeline execution aborted with error: {exc}",
            level="ERROR",
            source="orchestrator",
        )
    finally:
        pipeline_state["is_running"] = False
        finished_dt = datetime.now(UTC)
        pipeline_state["finished_at"] = finished_dt.isoformat()
        total_dur = round((finished_dt - start_dt).total_seconds(), 1)
        pipeline_state["duration_seconds"] = total_dur
        append_pipeline_log(
            f"Execution finished in {total_dur}s. Status: {pipeline_state['last_status']}",
            level="INFO",
            source="orchestrator",
        )


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
    res = dict(pipeline_state)
    if res.get("is_running") and res.get("started_at"):
        try:
            started = datetime.fromisoformat(res["started_at"])
            res["elapsed_seconds"] = round((datetime.now(UTC) - started).total_seconds(), 1)
        except Exception:
            res["elapsed_seconds"] = 0
    else:
        res["elapsed_seconds"] = res.get("duration_seconds")
    res["log_count"] = len(pipeline_logs)
    return res


@router.get("/pipeline-logs")
async def get_pipeline_logs(
    limit: int = Query(250, ge=1, le=1000),
    since: str | None = Query(None),
    level: str | None = Query(None),
    search: str | None = Query(None),
) -> dict[str, Any]:
    """Retrieve structured real-time logs for the execution terminal."""
    global pipeline_logs
    logs = list(pipeline_logs)

    # If in-memory is empty (e.g. server freshly restarted), pull recent logs from Prefect
    if not logs:
        try:
            prefect_url = os.getenv("PREFECT_API_URL", "http://prefect-server:4200/api")
            async with httpx.AsyncClient(timeout=4.0) as client:
                r = await client.post(
                    f"{prefect_url}/logs/filter",
                    json={"sort": "TIMESTAMP_DESC", "limit": limit},
                )
                if r.status_code == 200:
                    for log in reversed(r.json()):
                        lvl_num = log.get("level", 20)
                        lvl_str = "INFO"
                        if lvl_num >= 40:
                            lvl_str = "ERROR"
                        elif lvl_num >= 30:
                            lvl_str = "WARN"
                        msg = log.get("message", "")
                        if "[success]" in msg.lower():
                            lvl_str = "SUCCESS"
                        logs.append({
                            "id": log.get("id"),
                            "timestamp": log.get("timestamp"),
                            "level": lvl_str,
                            "source": log.get("name", "prefect"),
                            "flow_run_id": log.get("flow_run_id"),
                            "message": msg,
                        })
        except Exception as exc:
            logger.debug("Prefect log fallback query failed: %s", exc)

    if since:
        logs = [l for l in logs if str(l.get("timestamp", "")) > since]

    if level and level.upper() != "ALL":
        req_lvl = level.upper()
        logs = [l for l in logs if l.get("level") == req_lvl]

    if search:
        s_lower = search.strip().lower()
        logs = [
            l for l in logs
            if s_lower in l.get("message", "").lower()
            or s_lower in l.get("source", "").lower()
        ]

    return {
        "count": len(logs),
        "total_available": len(pipeline_logs),
        "is_running": pipeline_state.get("is_running", False),
        "current_stage": pipeline_state.get("current_stage"),
        "stage_index": pipeline_state.get("stage_index"),
        "progress_percent": pipeline_state.get("progress_percent", 0),
        "logs": logs[-limit:],
    }


@router.post("/pipeline-logs/clear")
def clear_pipeline_logs() -> dict[str, str]:
    """Clear in-memory telemetry logs buffer."""
    global pipeline_logs
    pipeline_logs.clear()
    return {"status": "cleared"}


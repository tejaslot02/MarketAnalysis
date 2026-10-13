"""Prefect ETL flow - the Transform + Load half of the pipeline.

  Extract  : scrapers XADD canonical JSON records to the Dragonfly stream `raw-jobs`.
  Transform: flows/transform.py enriches each record.
  Load     : upsert Postgres, index Elasticsearch, archive raw JSON to MinIO.

Run ad hoc:  python flows/scrape_flow.py
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import re
from datetime import UTC, datetime

import redis
try:
    from dlq_handler import route_to_dlq
    from transform import transform_record
except ModuleNotFoundError:
    from flows.dlq_handler import route_to_dlq
    from flows.transform import transform_record
from elasticsearch import Elasticsearch
from minio import Minio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from prefect import flow

DRAGONFLY_URL = os.getenv("DRAGONFLY_URL", "redis://dragonfly:6379/0")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/jobs",
)
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")

STREAM = "raw-jobs"
GROUP = "jobs-ingest"
CONSUMER = "consumer-1"
BATCH_SIZE = 100
ES_INDEX = "jobs"
MINIO_BUCKET = "raw-jobs"

UPSERT_SQL = text(
    """
    INSERT INTO jobs (
        id, source, external_id, title, company, location, is_remote,
        remote_type, salary_min, salary_max, salary_currency, salary_raw,
        base_vs_tc, posted_at, description, url, seniority, title_canonical,
        skills, responsibilities, salary_ok, raw
    ) VALUES (
        :id, :source, :external_id, :title, :company, :location, :is_remote,
        :remote_type, :salary_min, :salary_max, :salary_currency, :salary_raw,
        :base_vs_tc, :posted_at, :description, :url, :seniority, :title_canonical,
        CAST(:skills AS jsonb), CAST(:responsibilities AS jsonb), :salary_ok, CAST(:raw AS jsonb)
    )
    ON CONFLICT (id) DO UPDATE SET
        title            = EXCLUDED.title,
        company          = EXCLUDED.company,
        location         = EXCLUDED.location,
        is_remote        = EXCLUDED.is_remote,
        remote_type      = EXCLUDED.remote_type,
        salary_min       = EXCLUDED.salary_min,
        salary_max       = EXCLUDED.salary_max,
        salary_currency  = EXCLUDED.salary_currency,
        salary_raw       = EXCLUDED.salary_raw,
        base_vs_tc       = EXCLUDED.base_vs_tc,
        posted_at        = EXCLUDED.posted_at,
        description      = EXCLUDED.description,
        url              = EXCLUDED.url,
        seniority        = EXCLUDED.seniority,
        title_canonical  = EXCLUDED.title_canonical,
        skills           = EXCLUDED.skills,
        responsibilities = EXCLUDED.responsibilities,
        salary_ok        = EXCLUDED.salary_ok,
        raw              = EXCLUDED.raw,
        last_seen_at     = now()
    """
)
COMPANY_UPSERT_SQL = text(
    """
    INSERT INTO companies (id, name, first_seen_at, last_seen_at)
    VALUES (:id, :name, now(), now())
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        last_seen_at = now()
    """
)


def _company_params(record: dict) -> dict | None:
    name = (record.get("company") or "").strip()
    if not name:
        return None
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unknown"
    return {"id": slug, "name": name}


def _json(value):
    return json.dumps(value) if value is not None else None


def _record_params(record: dict) -> dict:
    return {
        "id": record.get("id"),
        "source": record.get("source"),
        "external_id": record.get("external_id"),
        "title": record.get("title"),
        "company": record.get("company"),
        "location": record.get("location"),
        "is_remote": record.get("is_remote", False),
        "remote_type": record.get("remote_type"),
        "salary_min": record.get("salary_min"),
        "salary_max": record.get("salary_max"),
        "salary_currency": record.get("salary_currency"),
        "salary_raw": record.get("salary_raw"),
        "base_vs_tc": record.get("base_vs_tc"),
        "posted_at": _parse_dt(record.get("posted_at")),
        "description": record.get("description"),
        "url": record.get("url"),
        "seniority": record.get("seniority"),
        "title_canonical": record.get("title_canonical"),
        "skills": _json(record.get("skills")),
        "responsibilities": _json(record.get("responsibilities")),
        "salary_ok": record.get("salary_ok", False),
        "raw": _json(record.get("raw")),
    }


def _parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _safe_date(value):
    if value is None:
        return None
    s = str(value)
    return s if re.match(r"^\d{4}-\d{2}-\d{2}", s) or re.match(r"^\d+$", s) else None


def _es_doc(record: dict) -> dict:
    return {
        "id": record.get("id"),
        "source": record.get("source"),
        "title": record.get("title"),
        "company": record.get("company"),
        "location": record.get("location"),
        "is_remote": record.get("is_remote", False),
        "remote_type": record.get("remote_type"),
        "salary_min": record.get("salary_min"),
        "salary_max": record.get("salary_max"),
        "salary_currency": record.get("salary_currency"),
        "base_vs_tc": record.get("base_vs_tc"),
        "posted_at": _safe_date(record.get("posted_at")),
        "description": record.get("description"),
        "url": record.get("url"),
        "seniority": record.get("seniority"),
        "title_canonical": record.get("title_canonical"),
        "skills": [s.get("name") for s in (record.get("skills") or [])],
        "responsibilities": [r.get("phrase") for r in (record.get("responsibilities") or [])],
        "salary_ok": record.get("salary_ok", False),
    }


def _archive(mc: Minio, raw: dict) -> None:
    data = json.dumps(raw).encode("utf-8")
    key = f"{raw.get('source', 'unknown')}/{raw.get('id', 'unknown')}.json"
    mc.put_object(MINIO_BUCKET, key, io.BytesIO(data), length=len(data), content_type="application/json")


def ensure_consumer_group(client: redis.Redis) -> None:
    try:
        client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except redis.exceptions.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def ensure_es_index(es: Elasticsearch) -> None:
    if not es.indices.exists(index=ES_INDEX):
        es.indices.create(
            index=ES_INDEX,
            mappings={
                "properties": {
                    "id": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "title": {"type": "text"},
                    "company": {"type": "keyword"},
                    "location": {"type": "text"},
                    "is_remote": {"type": "boolean"},
                    "remote_type": {"type": "keyword"},
                    "salary_min": {"type": "float"},
                    "salary_max": {"type": "float"},
                    "salary_currency": {"type": "keyword"},
                    "base_vs_tc": {"type": "keyword"},
                    "posted_at": {"type": "date", "format": "date_optional_time||epoch_millis||epoch_second"},
                    "description": {"type": "text"},
                    "url": {"type": "keyword"},
                    "seniority": {"type": "keyword"},
                    "title_canonical": {"type": "keyword"},
                    "skills": {"type": "keyword"},
                    "responsibilities": {"type": "text"},
                    "salary_ok": {"type": "boolean"},
                }
            },
        )
        print(f"[etl] created Elasticsearch index '{ES_INDEX}'")


def ensure_minio_bucket(mc: Minio) -> None:
    if not mc.bucket_exists(MINIO_BUCKET):
        mc.make_bucket(MINIO_BUCKET)
        print(f"[etl] created MinIO bucket '{MINIO_BUCKET}'")


async def _process_entries(client, engine, es, mc, entries) -> tuple[int, list[str]]:
    processed = 0
    acked: list[str] = []
    for message_id, fields in entries:
        try:
            raw = json.loads(fields.get("data", "{}"))
            record = transform_record(raw)

            async with engine.begin() as conn:
                await conn.execute(UPSERT_SQL, _record_params(record))

            cp = _company_params(record)
            if cp:
                try:
                    async with engine.begin() as conn:
                        await conn.execute(COMPANY_UPSERT_SQL, cp)
                except Exception as exc:  # noqa: BLE001
                    print(f"[etl] company upsert skipped ({exc})")

            es.index(index=ES_INDEX, id=record["id"], document=_es_doc(record))
            _archive(mc, raw)

            acked.append(message_id)
            processed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[etl] ERROR processing message {message_id}: {exc}. Routing to DLQ.")
            route_to_dlq(client, message_id, fields.get("data", "{}"), exc)
            acked.append(message_id)
    return processed, acked



async def consume_and_load(client, engine, es, mc) -> int:
    total = 0
    all_acked: list[str] = []
    try:
        # 1) reclaim pending messages stuck from a previous crashed run
        while True:
            _next, entries, _deleted = client.xautoclaim(
                STREAM, GROUP, CONSUMER, min_idle_time=5000, count=BATCH_SIZE
            )
            if not entries:
                break
            n, acked = await _process_entries(client, engine, es, mc, entries)
            total += n
            all_acked += acked
            if len(entries) < BATCH_SIZE:
                break

        # 2) read new messages until the stream is drained (loop in batches)
        while True:
            messages = client.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=BATCH_SIZE, block=1000)
            if not messages:
                break
            got = 0
            for _, entries in messages:
                n, acked = await _process_entries(client, engine, es, mc, entries)
                total += n
                all_acked += acked
                got += len(entries)
            if got < BATCH_SIZE:
                break
    finally:
        for mid in all_acked:
            client.xack(STREAM, GROUP, mid)
    return total


@flow(name="consume-raw-jobs")
async def etl_flow() -> int:
    client = redis.Redis.from_url(DRAGONFLY_URL, decode_responses=True)
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    es = Elasticsearch([ELASTICSEARCH_URL])
    mc = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)

    ensure_consumer_group(client)
    ensure_es_index(es)
    ensure_minio_bucket(mc)

    return await consume_and_load(client, engine, es, mc)


if __name__ == "__main__":
    processed = asyncio.run(etl_flow())
    print(f"[etl] processed {processed} job(s)")

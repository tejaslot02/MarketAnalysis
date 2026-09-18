"""Scraper service entrypoint (producer).

Per-portal Scrapy spiders are scheduled by Prefect (see flows/) and produce
canonical job records. This resident process emits whatever the spiders
produce to the Dragonfly stream `raw-jobs` via XADD; the Prefect flow
`consume-raw-jobs` (flows/scrape_flow.py) consumes the stream and persists
records to Postgres/MinIO.

This process also ensures the stream + consumer group exist on startup so the
consumer flow can XREADGROUP immediately.
"""

from __future__ import annotations

import json
import logging
import os
import time

import redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("scraper")

DRAGONFLY_URL = os.getenv("DRAGONFLY_URL", "redis://dragonfly:6379/0")
STREAM = "raw-jobs"
GROUP = "jobs-ingest"


def emit_job(record: dict) -> str:
    """XADD a canonical job record to the Dragonfly stream `raw-jobs`."""
    client = redis.Redis.from_url(DRAGONFLY_URL, decode_responses=True)
    message_id = client.xadd(STREAM, {"data": json.dumps(record)})
    log.info("Emitted job %s to %s (id=%s)", record.get("id"), STREAM, message_id)
    return message_id


def ensure_stream() -> None:
    """Ensure the stream and consumer group exist so the consumer can attach."""
    client = redis.Redis.from_url(DRAGONFLY_URL, decode_responses=True)
    try:
        client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        log.info("Created consumer group %s on stream %s", GROUP, STREAM)
    except redis.exceptions.ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            log.info("Consumer group %s already exists", GROUP)
        else:
            raise


def main() -> None:
    log.info("Scraper producer started (Dragonfly Redis Streams: %s)", DRAGONFLY_URL)
    ensure_stream()
    log.info("Portals live in scrapers/portals/. Schedule them via Prefect flows (flows/).")
    # Resident loop: Prefect schedules the actual per-portal spiders; this
    # process stays alive emitting whatever those spiders produce.
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

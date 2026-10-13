"""Scrapy item pipeline: XADD normalized job records to the Dragonfly stream.

This is the hand-off from Extract (spiders) to the Prefect 'consume-raw-jobs'
flow, which XREADGROUPs the stream, enriches, and loads to Postgres/ES/MinIO.
"""
from __future__ import annotations

import json
import logging
import os

import redis

log = logging.getLogger(__name__)

DRAGONFLY_URL = os.getenv("DRAGONFLY_URL", "redis://dragonfly:6379/0")
STREAM = os.getenv("STREAM_NAME", "raw-jobs")
GROUP = os.getenv("STREAM_GROUP", "jobs-ingest")


class DragonflyStreamPipeline:
    """XADD each item to the `raw-jobs` stream as JSON."""

    def open_spider(self, spider):
        self.client = redis.Redis.from_url(DRAGONFLY_URL, decode_responses=True)
        try:
            self.client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        except redis.exceptions.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        return self

    def close_spider(self, spider):
        if getattr(self, "client", None):
            self.client.close()

    def process_item(self, item, spider):
        record = dict(item)
        self.client.xadd(STREAM, {"data": json.dumps(record)}, maxlen=100000, approximate=True)
        log.info("XADD %s id=%s (trimmed maxlen=100000)", STREAM, record.get("id"))
        return item


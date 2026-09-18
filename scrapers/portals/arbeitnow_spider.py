"""Arbeitnow job-board API spider (https://www.arbeitnow.com/api/job-board-api)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator

import scrapy

from .common import base_record, stable_id, strip_html


def _iso(ts: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


class ArbeitnowSpider(scrapy.Spider):
    name = "arbeitnow"
    allowed_domains = ["arbeitnow.com"]
    start_urls = ["https://www.arbeitnow.com/api/job-board-api"]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        data = response.json()
        for job in data.get("data", []) or []:
            yield self._normalize(job)

    def _normalize(self, job: dict[str, Any]) -> dict[str, Any]:
        ext = str(job.get("slug", ""))
        remote = bool(job.get("remote"))
        return base_record(
            id=stable_id("arbeitnow", ext),
            source="arbeitnow",
            external_id=ext,
            title=job.get("title", ""),
            company=job.get("company_name", ""),
            location=job.get("location", ""),
            is_remote=remote,
            remote_type="fully_remote" if remote else None,
            posted_at=_iso(job.get("created_at")),
            description=strip_html(job.get("description") or ""),
            url=job.get("url", ""),
            raw=job,
        )

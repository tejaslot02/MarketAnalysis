"""Himalayas remote-jobs API spider (https://himalayas.app/jobs/api)."""
from __future__ import annotations

from typing import Any, Iterator

import scrapy

from .common import base_record, stable_id


def _int(v: Any) -> int | None:
    try:
        n = int(float(v))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


class HimalayasSpider(scrapy.Spider):
    name = "himalayas"
    allowed_domains = ["himalayas.app"]
    start_urls = ["https://himalayas.app/jobs/api"]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        data = response.json()
        if isinstance(data, list):
            jobs = data
        elif isinstance(data, dict):
            jobs = data.get("jobs", []) or []
        else:
            jobs = []
        for job in jobs:
            yield self._normalize(job)

    def _normalize(self, job: dict[str, Any]) -> dict[str, Any]:
        ext = str(job.get("id", "") or job.get("guid", ""))
        salary = job.get("salary") or {}
        return base_record(
            id=stable_id("himalayas", ext),
            source="himalayas",
            external_id=ext,
            title=job.get("title", ""),
            company=job.get("companyName", ""),
            location=job.get("location", "") or "",
            is_remote=True,
            remote_type="fully_remote",
            salary_min=_int((salary or {}).get("min")),
            salary_max=_int((salary or {}).get("max")),
            posted_at=job.get("datePosted") or job.get("pubDate"),
            description=job.get("description", "") or "",
            url=job.get("url", ""),
            raw=job,
        )

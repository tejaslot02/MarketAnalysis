"""Working Nomads JSON API spider (https://www.workingnomads.com/api/exposed_jobs/)."""
from __future__ import annotations

from typing import Any, Iterator

import scrapy

from .common import base_record, stable_id


class WorkingNomadsSpider(scrapy.Spider):
    name = "workingnomads"
    allowed_domains = ["workingnomads.com"]
    start_urls = ["https://www.workingnomads.com/api/exposed_jobs/"]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        data = response.json()
        if isinstance(data, list):
            jobs = data
        elif isinstance(data, dict):
            jobs = data.get("jobs", []) or data.get("data", []) or []
        else:
            jobs = []
        for job in jobs:
            yield self._normalize(job)

    def _normalize(self, job: dict[str, Any]) -> dict[str, Any]:
        ext = str(job.get("id") or job.get("slug") or job.get("url") or "")
        return base_record(
            id=stable_id("workingnomads", ext),
            source="workingnomads",
            external_id=ext,
            title=job.get("title") or job.get("job_title") or "",
            company=job.get("company_name") or job.get("company") or "",
            location=job.get("location") or "",
            is_remote=True,
            remote_type="fully_remote",
            posted_at=job.get("post_date") or job.get("date") or job.get("created_at"),
            description=job.get("description") or "",
            url=job.get("url") or "",
            raw=job,
        )

"""Remotive spider via its public JSON API (https://remotive.com/api/remote-jobs).

Collects ALL remote jobs (no search filter); classification happens downstream.
"""
from __future__ import annotations

from typing import Any, Iterator

import scrapy

from .common import base_record, extract_salary, stable_id


class RemotiveSpider(scrapy.Spider):
    name = "remotive"
    allowed_domains = ["remotive.com"]

    def __init__(self, search: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search = search
        url = "https://remotive.com/api/remote-jobs?limit=200"
        if search:
            url += f"&search={search}"
        self.start_urls = [url]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        data = response.json()
        for job in data.get("jobs", []) or []:
            yield self._normalize(job)

    def _normalize(self, job: dict[str, Any]) -> dict[str, Any]:
        ext = str(job.get("id", ""))
        sal = str(job.get("salary") or "")
        mn, mx = extract_salary(sal)
        return base_record(
            id=stable_id("remotive", ext),
            source="remotive",
            external_id=ext,
            title=job.get("title", ""),
            company=job.get("company_name", ""),
            location=job.get("candidate_required_location", ""),
            is_remote=True,
            remote_type="fully_remote",
            salary_min=mn,
            salary_max=mx,
            salary_raw=sal or None,
            posted_at=job.get("publication_date"),
            description=job.get("description", ""),
            url=job.get("url", ""),
            raw=job,
        )

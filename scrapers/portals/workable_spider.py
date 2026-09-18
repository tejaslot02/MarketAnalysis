"""Workable ATS spider via its public JSON API.

Usage: scrapy crawl workable -a account=<account-slug>
"""
from __future__ import annotations

from typing import Any, Iterator

import scrapy

from .common import base_record, is_remote_text, stable_id, strip_html


class WorkableSpider(scrapy.Spider):
    name = "workable"
    allowed_domains = ["apply.workable.com"]

    def __init__(self, account: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not account:
            raise ValueError("account slug is required, e.g. -a account=huggingface")
        self.account = account
        self.start_urls = [
            f"https://apply.workable.com/api/v3/accounts/{account}/jobs?limit=100"
        ]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        data = response.json()
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        for job in jobs:
            yield self._normalize(job)

    def _normalize(self, job: dict[str, Any]) -> dict[str, Any]:
        ext = str(job.get("id", "") or job.get("shortcode", ""))
        loc = job.get("location") or {}
        if not isinstance(loc, dict):
            loc = {}
        parts = [loc.get("city"), loc.get("region"), loc.get("country")]
        location = ", ".join([p for p in parts if p]) or None
        is_remote = bool(loc.get("telecommuting")) or (loc.get("workplace_type") == "remote") or is_remote_text(location)
        sr = job.get("salary_range") or {}
        return base_record(
            id=stable_id("workable", self.account, ext),
            source="workable",
            external_id=ext,
            title=job.get("title", ""),
            company=self.account,
            location=location,
            is_remote=is_remote,
            remote_type="fully_remote" if is_remote else None,
            salary_min=(sr or {}).get("min"),
            salary_max=(sr or {}).get("max"),
            posted_at=job.get("published_on"),
            description=strip_html(job.get("description") or ""),
            url=job.get("url") or job.get("application_url", ""),
            raw=job,
        )

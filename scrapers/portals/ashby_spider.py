"""Ashby ATS spider via its public JSON API.

Usage: scrapy crawl ashby -a org=<organization-slug>
"""
from __future__ import annotations

from typing import Any, Iterator

import scrapy

from .common import base_record, is_remote_text, stable_id, strip_html


class AshbySpider(scrapy.Spider):
    name = "ashby"
    allowed_domains = ["api.ashbyhq.com"]

    def __init__(self, org: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not org:
            raise ValueError("org slug is required, e.g. -a org=openai")
        self.org = org
        self.start_urls = [f"https://api.ashbyhq.com/posting-api/job-board/{org}"]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        data = response.json()
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        for job in jobs:
            yield self._normalize(job)

    def _normalize(self, job: dict[str, Any]) -> dict[str, Any]:
        ext = str(job.get("id", ""))
        location = job.get("location") or ""
        is_remote = bool(job.get("isRemote")) or is_remote_text(location)
        sal_min = sal_max = None
        comp = job.get("compensation") or {}
        if isinstance(comp, dict):
            comps = comp.get("summaryComponents") or comp.get("components") or []
            for c in comps if isinstance(comps, list) else []:
                if isinstance(c, dict) and c.get("compensationType") in ("Base", "base"):
                    sal_min = c.get("minValue")
                    sal_max = c.get("maxValue")
        desc_html = job.get("descriptionHtml") or job.get("description") or ""
        return base_record(
            id=stable_id("ashby", self.org, ext),
            source="ashby",
            external_id=ext,
            title=job.get("title", ""),
            company=self.org,
            location=location,
            is_remote=is_remote,
            remote_type="fully_remote" if is_remote else None,
            salary_min=sal_min,
            salary_max=sal_max,
            salary_raw=None,
            posted_at=job.get("publishedAt") or job.get("createdAt"),
            description=strip_html(desc_html),
            url=job.get("applyUrl", ""),
            raw=job,
        )

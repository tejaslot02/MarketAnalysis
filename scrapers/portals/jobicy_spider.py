"""Jobicy remote-jobs API spider (https://jobicy.com/api/v2/remote-jobs)."""
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


class JobicySpider(scrapy.Spider):
    name = "jobicy"
    allowed_domains = ["jobicy.com"]

    def __init__(self, count: str = "200", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.start_urls = [f"https://jobicy.com/api/v2/remote-jobs?count={count}"]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        data = response.json()
        for job in data.get("jobs", []) or []:
            yield self._normalize(job)

    def _normalize(self, job: dict[str, Any]) -> dict[str, Any]:
        ext = str(job.get("id", ""))
        return base_record(
            id=stable_id("jobicy", ext),
            source="jobicy",
            external_id=ext,
            title=job.get("jobTitle", ""),
            company=job.get("companyName", ""),
            location=job.get("jobGeo", ""),
            is_remote=True,
            remote_type="fully_remote",
            salary_min=_int(job.get("annualSalaryMin")),
            salary_max=_int(job.get("annualSalaryMax")),
            salary_currency=job.get("salaryCurrency") or "USD",
            salary_raw=job.get("salary"),
            posted_at=job.get("pubDate"),
            description=job.get("jobDescription") or job.get("jobExcerpt") or "",
            url=job.get("url", ""),
            raw=job,
        )

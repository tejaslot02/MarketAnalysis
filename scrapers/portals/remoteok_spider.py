"""RemoteOK spider via its public JSON API (https://remoteok.com/api).

Collects ALL remote jobs (no tag filter); classification/salary signals are
applied downstream in enrichment so nothing is dropped at ingest.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterator

import scrapy


class RemoteOKSpider(scrapy.Spider):
    name = "remoteok"
    allowed_domains = ["remoteok.com"]

    def __init__(self, tag: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tag = tag
        url = "https://remoteok.com/api" if not tag else f"https://remoteok.com/api?tag={tag}"
        self.start_urls = [url]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        data = json.loads(response.text)
        # RemoteOK returns a JSON array whose first element is a metadata row.
        for job in data[1:]:
            if isinstance(job, dict):
                yield self._normalize(job)

    def _normalize(self, job: dict[str, Any]) -> dict[str, Any]:
        external_id = str(job.get("id", ""))
        title = job.get("position", "")
        location = job.get("location", "")

        def _int(v):
            try:
                n = int(v)
                return n if n > 0 else None
            except (TypeError, ValueError):
                return None

        return {
            "id": hashlib.sha256(f"remoteok:{external_id}".encode()).hexdigest(),
            "source": "remoteok",
            "external_id": external_id,
            "title": title,
            "company": job.get("company", ""),
            "location": location,
            "is_remote": True,
            "remote_type": "fully_remote",
            "salary_min": _int(job.get("salary_min")),
            "salary_max": _int(job.get("salary_max")),
            "salary_currency": "USD",
            "salary_raw": None,
            "base_vs_tc": "unknown",
            "posted_at": job.get("date"),
            "description": job.get("description", ""),
            "url": job.get("url", ""),
            "seniority": None,
            "title_canonical": None,
            "skills": [],
            "responsibilities": [],
            "salary_ok": False,
            "raw": job,
        }

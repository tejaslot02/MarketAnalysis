"""Greenhouse ATS spider via its public JSON API.

Default: board job list only (fast discovery). Pass `-a fetch_details=true` to
follow each job's detail endpoint and capture the full description (`content`)
for a separate (slower) enrichment pass.

Run:  scrapy crawl greenhouse -a board_token=companyname
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Iterator

import scrapy


class GreenhouseSpider(scrapy.Spider):
    name = "greenhouse"
    allowed_domains = ["boards-api.greenhouse.io"]

    # JSON API (not HTML) -> fixed higher concurrency, no autothrottle ramp-up.
    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 8,
        "DOWNLOAD_DELAY": 0.5,
        "AUTOTHROTTLE_ENABLED": False,
    }

    def __init__(self, board_token: str = "", fetch_details: str = "false", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.board_token = board_token
        if not board_token:
            raise ValueError("board_token is required, e.g. -a board_token=companyname")
        self.fetch_details = str(fetch_details).lower() in ("1", "true", "yes")
        self.start_urls = [
            f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
        ]

    def parse(self, response: scrapy.http.Response) -> Iterator[Any]:
        jobs = response.json().get("jobs", [])
        for job in jobs:
            if self.fetch_details:
                detail_url = (
                    f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs/{job.get('id')}"
                )
                yield scrapy.Request(detail_url, callback=self.parse_detail, meta={"job": job})
            else:
                yield self._normalize(job)

    def parse_detail(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        job = response.meta["job"]
        detail = response.json()
        yield self._normalize(job, detail.get("content", ""))

    def _normalize(self, job: dict[str, Any], description: str = "") -> dict[str, Any]:
        """Map a source record (plus optional detail content) to the canonical schema."""
        title = job.get("title", "")
        external_id = str(job.get("id", ""))
        stable_id = hashlib.sha256(
            f"greenhouse:{self.board_token}:{external_id}".encode()
        ).hexdigest()

        location = (
            job.get("location", {}).get("name", "")
            if isinstance(job.get("location"), dict)
            else str(job.get("location", ""))
        )
        remote = self._is_remote(location, title)

        return {
            "id": stable_id,
            "source": "greenhouse",
            "external_id": external_id,
            "title": title,
            "company": self.board_token,
            "location": location,
            "is_remote": remote,
            "remote_type": "fully_remote" if remote else None,
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
            "salary_raw": None,
            "base_vs_tc": "unknown",
            "posted_at": job.get("updated_at"),
            "description": re.sub(r"<[^>]+>", " ", description or ""),
            "url": job.get("absolute_url", ""),
            "seniority": None,
            "title_canonical": None,
            "skills": [],
            "responsibilities": [],
            "salary_ok": False,
            "raw": {**job, "content": description},
        }

    @staticmethod
    def _is_remote(location: str, title: str) -> bool:
        text = f"{location} {title}".lower()
        return any(tok in text for tok in ("remote", "anywhere", "work from home"))

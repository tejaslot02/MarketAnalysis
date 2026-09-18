"""Example scraper: Greenhouse board via its public JSON API.

Demonstrates the per-portal adapter pattern:
  1. Fetch source JSON (API-first — no HTML parsing needed).
  2. Normalize to the canonical job record (see docs/PLAN.md schema).
  3. Yield the record; the producer XADDs it to the Dragonfly stream raw-jobs (see run.py).

Run:
  scrapy runspider scrapers/portals/example_spider.py \
    -a board_token=companyname
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterator

import scrapy


class GreenhouseSpider(scrapy.Spider):
    name = "greenhouse"
    allowed_domains = ["boards-api.greenhouse.io"]

    def __init__(self, board_token: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.board_token = board_token
        if not board_token:
            raise ValueError("board_token is required, e.g. -a board_token=companyname")
        self.start_urls = [
            f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
        ]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        jobs = response.json().get("jobs", [])
        for job in jobs:
            yield self._normalize(job)

    # ------------------------------------------------------------------ #
    def _normalize(self, job: dict[str, Any]) -> dict[str, Any]:
        """Map a source record to the canonical job schema."""
        title = job.get("title", "")
        external_id = str(job.get("id", ""))
        stable_id = hashlib.sha256(
            f"greenhouse:{self.board_token}:{external_id}".encode()
        ).hexdigest()

        location = job.get("location", {}).get("name", "") if isinstance(job.get("location"), dict) else str(job.get("location", ""))

        return {
            "id": stable_id,
            "source": "greenhouse",
            "external_id": external_id,
            "title": title,
            "company": self.board_token,
            "location": location,
            "is_remote": self._is_remote(location, title),
            "remote_type": "fully_remote" if self._is_remote(location, title) else None,
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
            "salary_raw": None,
            "base_vs_tc": "unknown",
            "posted_at": None,  # Greenhouse jobs API omits dates; re-check detail endpoint
            "description": "",
            "url": job.get("absolute_url", ""),
            "seniority": None,  # filled by enrichment pipeline
            "title_canonical": None,
            "skills": [],
            "responsibilities": [],
            "salary_ok": False,
            "raw": job,
        }

    @staticmethod
    def _is_remote(location: str, title: str) -> bool:
        text = f"{location} {title}".lower()
        return any(tok in text for tok in ("remote", "anywhere", "work from home"))

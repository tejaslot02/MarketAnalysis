"""Lever ATS spider via its public JSON API.

Usage: scrapy crawl lever -a company=<company-slug>
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Iterator

import scrapy


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "")


def _extract_salary(text: str):
    m = re.search(r"\$(\d{1,3}(?:,\d{3})*)\s*[-\u2013\u2014]\s*\$(\d{1,3}(?:,\d{3})*)", text)
    if m:
        return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
    m = re.search(r"\$(\d{1,3}(?:,\d{3})*)\s*[kK]", text)
    if m:
        v = int(m.group(1).replace(",", "")) * 1000
        return v, None
    return None, None


class LeverSpider(scrapy.Spider):
    name = "lever"
    allowed_domains = ["api.lever.co"]

    def __init__(self, company: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not company:
            raise ValueError("company slug is required, e.g. -a company=openai")
        self.company = company
        self.start_urls = [f"https://api.lever.co/v0/postings/{company}?mode=json"]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        data = response.json()
        postings = data if isinstance(data, list) else data.get("postings", [])
        for job in postings:
            if isinstance(job, dict):
                yield self._normalize(job)

    def _normalize(self, job: dict[str, Any]) -> dict[str, Any]:
        external_id = str(job.get("id", ""))
        cats = job.get("categories", {}) or {}
        location = cats.get("location") or cats.get("allLocations") or ""
        workplace = cats.get("workplaceType") or cats.get("workplace") or ""
        desc_html = job.get("description", "") or ""
        desc = _strip_html(desc_html)
        sal_min, sal_max = _extract_salary(desc)
        created = job.get("createdAt")
        posted = None
        if created:
            try:
                posted = datetime.fromtimestamp(created / 1000, tz=timezone.utc).isoformat()
            except (TypeError, OSError, ValueError):
                posted = None

        return {
            "id": hashlib.sha256(f"lever:{self.company}:{external_id}".encode()).hexdigest(),
            "source": "lever",
            "external_id": external_id,
            "title": job.get("text", ""),
            "company": self.company,
            "location": location,
            "is_remote": "remote" in f"{location} {workplace}".lower(),
            "remote_type": "fully_remote" if "remote" in f"{location} {workplace}".lower() else None,
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_currency": "USD",
            "salary_raw": None,
            "base_vs_tc": "unknown",
            "posted_at": posted,
            "description": desc,
            "url": job.get("hostedUrl", ""),
            "seniority": None,
            "title_canonical": None,
            "skills": [],
            "responsibilities": [],
            "salary_ok": False,
            "raw": job,
        }

"""Hacker News 'Who is hiring?' thread via the official Firebase API.

Usage: scrapy crawl hn -a item_id=<current-month-thread-id>
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterator

import scrapy


class HNSpider(scrapy.Spider):
    name = "hn"
    allowed_domains = ["hacker-news.firebaseio.com"]

    def __init__(self, item_id: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not item_id:
            raise ValueError("item_id is required (the 'Who is hiring?' thread id)")
        self.item_id = item_id
        self.start_urls = [f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"]

    def parse(self, response: scrapy.http.Response) -> Iterator[scrapy.Request]:
        thread = response.json()
        for kid in thread.get("kids", []):
            yield scrapy.Request(
                f"https://hacker-news.firebaseio.com/v0/item/{kid}.json",
                callback=self.parse_job,
            )

    def parse_job(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        comment = response.json() or {}
        text = comment.get("text", "") or ""
        first_line = text.split("\n", 1)[0] if text else ""
        parts = [p.strip() for p in first_line.split("|")]
        company = parts[0] if len(parts) > 0 else ""
        title = parts[1] if len(parts) > 1 else ""
        location = parts[2] if len(parts) > 2 else ""
        remote = parts[3] if len(parts) > 3 else ""
        external_id = str(comment.get("id", ""))
        is_remote = "remote" in f"{location} {remote}".lower()

        yield {
            "id": hashlib.sha256(f"hn:{external_id}".encode()).hexdigest(),
            "source": "hn",
            "external_id": external_id,
            "title": title or first_line[:80],
            "company": company,
            "location": location,
            "is_remote": is_remote,
            "remote_type": "fully_remote" if is_remote else None,
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
            "salary_raw": None,
            "base_vs_tc": "unknown",
            "posted_at": None,
            "description": text,
            "url": f"https://news.ycombinator.com/item?id={external_id}",
            "seniority": None,
            "title_canonical": None,
            "skills": [],
            "responsibilities": [],
            "salary_ok": False,
            "raw": comment,
        }

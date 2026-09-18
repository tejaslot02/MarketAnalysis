"""aijobs.net spider (HTML, best-effort).

The site has no public API and its markup changes; this spider tries a few
common selectors and degrades gracefully. Verify against the live DOM before
relying on it. Politeness settings (robots.txt, delays) are applied globally
via settings.py.
"""
from __future__ import annotations

from typing import Any, Iterator

import scrapy

from .common import base_record, stable_id


class AIJobsSpider(scrapy.Spider):
    name = "aijobs"
    allowed_domains = ["aijobs.net"]
    start_urls = ["https://aijobs.net/"]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        cards = response.css("a[href*='/job/'], a[href*='/jobs/'], article")
        seen = set()
        for card in cards:
            link = card.css("a::attr(href)").get() or card.attrib.get("href") or ""
            title = (card.css("h2::text, h3::text, h4::text").get() or "").strip()
            if not (title and link):
                continue
            url = response.urljoin(link)
            if url in seen:
                continue
            seen.add(url)
            company = (card.css("[class*='company']::text, .company::text").get() or "").strip()
            location = (card.css("[class*='location']::text, .location::text").get() or "").strip()
            yield base_record(
                id=stable_id("aijobs", url),
                source="aijobs",
                external_id=url,
                title=title,
                company=company or None,
                location=location or None,
                is_remote="remote" in f"{location} {title}".lower(),
                url=url,
                raw={"url": url, "title": title, "company": company, "location": location},
            )

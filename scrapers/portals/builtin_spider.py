"""Built In jobs spider (HTML, best-effort).

No public API. Built In's remote+salary-filtered listing is scraped politely.
Markup changes frequently -- verify selectors against the live site.
"""
from __future__ import annotations

from typing import Any, Iterator

import scrapy

from .common import base_record, stable_id


class BuiltInSpider(scrapy.Spider):
    name = "builtin"
    allowed_domains = ["builtin.com"]
    start_urls = ["https://builtin.com/jobs/remote"]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        cards = response.css("a[href*='/job/']")
        seen = set()
        for a in cards:
            link = a.attrib.get("href", "")
            title = (a.css("h2::text, h3::text, h4::text").get() or a.attrib.get("title") or "").strip()
            if not (title and link):
                continue
            url = response.urljoin(link)
            if url in seen:
                continue
            seen.add(url)
            company = (a.css("[class*='company']::text").get() or "").strip()
            location = (a.css("[class*='location']::text").get() or "").strip()
            yield base_record(
                id=stable_id("builtin", url),
                source="builtin",
                external_id=url,
                title=title,
                company=company or None,
                location=location or None,
                is_remote="remote" in f"{location} {title}".lower(),
                url=url,
                raw={"url": url, "title": title, "company": company, "location": location},
            )

"""We Work Remotely spider via its per-category RSS feed."""
from __future__ import annotations

from typing import Any, Iterator

import scrapy

from .common import base_record, split_title_company, stable_id


class WeWorkRemotelySpider(scrapy.Spider):
    name = "weworkremotely"
    allowed_domains = ["weworkremotely.com"]
    start_urls = ["https://weworkremotely.com/categories/remote-programming-jobs.rss"]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        response.selector.remove_namespaces()
        for item in response.xpath("//item"):
            title_raw = (item.xpath("string(title)").get() or "").strip()
            link = (item.xpath("string(link)").get() or "").strip()
            pub = (item.xpath("string(pubDate)").get() or "").strip()
            desc = (item.xpath("string(description)").get() or "").strip()
            guid = (item.xpath("string(guid)").get() or link).strip()
            title, company = split_title_company(title_raw)
            ext = guid or link
            yield base_record(
                id=stable_id("weworkremotely", ext),
                source="weworkremotely",
                external_id=ext,
                title=title,
                company=company or None,
                location=None,
                is_remote=True,
                remote_type="fully_remote",
                posted_at=pub or None,
                description=desc,
                url=link,
                raw={"title": title_raw, "link": link, "pubDate": pub, "guid": guid},
            )

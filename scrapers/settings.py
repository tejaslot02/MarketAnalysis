"""Scrapy settings for the job-search ETL 'Extract' stage."""
import os

BOT_NAME = "job_search"

SPIDER_MODULES = ["portals"]
NEWSPIDER_MODULE = "portals"

# Push each normalized job record into Dragonfly (Redis Streams).
ITEM_PIPELINES = {
    "pipelines.DragonflyStreamPipeline": 300,
}

# Politeness / compliance (see docs/COMPLIANCE.md)
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
RETRY_TIMES = 3
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

USER_AGENT = os.getenv("USER_AGENT", "JobSearchBot/1.0 (+contact: admin@example.com)")

COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False
LOG_LEVEL = "INFO"

DEFAULT_REQUEST_HEADERS = {"Accept": "application/json,text/html,*/*"}

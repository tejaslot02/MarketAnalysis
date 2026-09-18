"""Prefect scheduler: serve deployments with schedules.

Replaces the work-pool worker with in-process `prefect.serve` (Prefect 3).
Deployments:
  seed-master-data  -> daily (default 06:30 America/New_York)
  scrape-portals    -> daily (default 07:00 America/New_York)
  consume-raw-jobs  -> every CONSUME_INTERVAL_SECONDS (default 1800)

Run:  python flows/scheduler.py
"""
from __future__ import annotations

import os

import prefect
from prefect.client.schemas.schedules import CronSchedule, IntervalSchedule

from scrape_flow import etl_flow
from scrape_portals import scrape_portals_flow
from seed_master_data import seed_master_data_flow

SEED_CRON = os.getenv("SEED_CRON", "30 6 * * *")
SCRAPE_CRON = os.getenv("SCRAPE_CRON", "0 7 * * *")
CONSUME_INTERVAL = int(os.getenv("CONSUME_INTERVAL_SECONDS", "1800"))
TIMEZONE = os.getenv("SCHEDULE_TIMEZONE", "America/New_York")


def _serve() -> None:
    prefect.serve(
        seed_master_data_flow.to_deployment(
            name="seed-master-data",
            schedules=[CronSchedule(cron=SEED_CRON, timezone=TIMEZONE)],
            tags=["master-data"],
        ),
        scrape_portals_flow.to_deployment(
            name="scrape-portals-daily",
            schedules=[CronSchedule(cron=SCRAPE_CRON, timezone=TIMEZONE)],
            tags=["ingest"],
        ),
        etl_flow.to_deployment(
            name="consume-raw-jobs",
            schedules=[IntervalSchedule(interval=CONSUME_INTERVAL)],
            tags=["etl"],
        ),
    )


if __name__ == "__main__":
    _serve()

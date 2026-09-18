"""Prefect scheduler: serve deployments with schedules.

Replaces the work-pool worker with in-process `prefect.serve` (Prefect 3).
Deployments:
  seed-master-data  -> daily (default 06:30 America/New_York)
  scrape-portals    -> daily (default 07:00 America/New_York)
  consume-raw-jobs  -> every CONSUME_INTERVAL_SECONDS (default 1800)
  snapshot-analytics -> daily (default 08:30 America/New_York)

Run:  python flows/scheduler.py
"""
from __future__ import annotations

import os

import prefect
from prefect.client.schemas.schedules import CronSchedule, IntervalSchedule

from scrape_flow import etl_flow
from scrape_portals import scrape_portals_flow
from seed_master_data import seed_master_data_flow
from snapshot_analytics import snapshot_analytics_flow
from mine_skills import mine_skills_flow

SEED_CRON = os.getenv("SEED_CRON", "30 6 * * *")
SCRAPE_CRON = os.getenv("SCRAPE_CRON", "0 7 * * *")
CONSUME_INTERVAL = int(os.getenv("CONSUME_INTERVAL_SECONDS", "1800"))
TIMEZONE = os.getenv("SCHEDULE_TIMEZONE", "America/New_York")
SNAPSHOT_CRON = os.getenv("SNAPSHOT_CRON", "30 8 * * *")
MINE_CRON = os.getenv("MINE_CRON", "0 9 * * *")


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
        snapshot_analytics_flow.to_deployment(
            name="snapshot-analytics",
            schedules=[CronSchedule(cron=SNAPSHOT_CRON, timezone=TIMEZONE)],
            tags=["analytics"],
        ),
        mine_skills_flow.to_deployment(
            name="mine-skills",
            schedules=[CronSchedule(cron=MINE_CRON, timezone=TIMEZONE)],
            tags=["analytics"],
        ),
        etl_flow.to_deployment(
            name="consume-raw-jobs",
            schedules=[IntervalSchedule(interval=CONSUME_INTERVAL)],
            tags=["etl"],
        ),
    )


if __name__ == "__main__":
    _serve()

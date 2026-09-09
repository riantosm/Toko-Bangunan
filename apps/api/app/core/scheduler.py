import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from app.core.config import settings
from app.core.db import SessionLocal
from app.reports.daily import run_daily_report

logger = logging.getLogger("app.scheduler")


async def _nightly_report_job() -> None:
    async with SessionLocal() as session:
        result = await run_daily_report(session)
    logger.info("scheduled nightly report: %s", result.get("status"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    scheduler: AsyncIOScheduler | None = None

    if settings.scheduler_enabled:
        scheduler = AsyncIOScheduler(timezone="Asia/Jakarta")
        scheduler.add_job(
            _nightly_report_job,
            CronTrigger(hour=settings.scheduler_report_cron_hour, minute=0),
            id="nightly_report",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.start()
        logger.info(
            "scheduler on: nightly_report at %02d:00 Asia/Jakarta",
            settings.scheduler_report_cron_hour,
        )
    else:
        logger.info("scheduler off (SCHEDULER_ENABLED=false)")

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)

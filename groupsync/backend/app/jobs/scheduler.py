import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.jobs.deadline_checker import run_deadline_checks

log = logging.getLogger(__name__)


def start_scheduler() -> BackgroundScheduler | None:
    if not settings.scheduler_enabled:
        return None
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_deadline_checks,
        "interval",
        minutes=settings.deadline_check_interval_minutes,
        id="deadline_checks",
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now() + timedelta(seconds=30),  # first run shortly after startup
    )
    scheduler.start()
    log.info("Scheduler started")
    return scheduler

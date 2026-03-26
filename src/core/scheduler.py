import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from core.config import AppConfig
from core.database import Database
from core.orchestrator import run_research_cycle

logger = logging.getLogger(__name__)


def start(config: AppConfig, db: Database):
    sched = config.schedule

    scheduler = BlockingScheduler()

    def _run():
        try:
            run_research_cycle(config, db)
        except Exception as exc:
            logger.error(f"Scheduled cycle raised unexpectedly: {exc}", exc_info=True)

    scheduler.add_job(
        _run,
        CronTrigger(
            hour=sched.hour,
            minute=sched.minute,
            timezone=sched.timezone,
        ),
        id="daily_research",
        name=f"Daily research — {config.product.name}",
        misfire_grace_time=3600,  # fire up to 1 hour late if server was offline
        replace_existing=True,
    )

    def _shutdown(signum, frame):
        logger.info("Shutdown signal received — stopping scheduler")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info(
        f"Scheduler started — daily briefing at "
        f"{sched.hour:02d}:{sched.minute:02d} {sched.timezone}"
    )
    scheduler.start()

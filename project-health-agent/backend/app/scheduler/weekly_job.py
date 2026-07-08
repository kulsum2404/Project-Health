"""
Weekly scheduler — runs project analysis on a cron schedule.

Uses APScheduler with a cron trigger. Disabled by default in dev.
Configure via SCHEDULER_ENABLED and SCHEDULER_CRON env vars.
"""

from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select

from app.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def run_weekly_analysis() -> None:
    """
    Run analysis on all active projects.
    This is the job function triggered by the scheduler.
    """
    from app.api.projects import analyze_project
    from app.main import get_engine
    from app.models.models import Project

    logger.info("Starting scheduled weekly analysis at %s", datetime.utcnow().isoformat())

    engine = get_engine()
    with Session(engine) as session:
        projects = session.exec(
            select(Project).where(Project.is_active == True)  # noqa: E712
        ).all()

        logger.info("Found %d active projects to analyze", len(projects))

        for project in projects:
            try:
                logger.info("Analyzing project: %s (id=%d)", project.name, project.id)
                # Create a new session for each project analysis
                with Session(engine) as proj_session:
                    await analyze_project(project.id, proj_session)  # type: ignore
                logger.info("Analysis complete for project: %s", project.name)
            except Exception as e:
                logger.error(
                    "Failed to analyze project %s (id=%d): %s",
                    project.name, project.id, e,  # type: ignore
                )

    logger.info("Weekly analysis complete")


def start_scheduler() -> None:
    """Start the APScheduler with the configured cron expression."""
    global _scheduler

    settings = get_settings()

    if not settings.scheduler_enabled:
        logger.info("Scheduler is disabled (SCHEDULER_ENABLED=false)")
        return

    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return

    _scheduler = AsyncIOScheduler()

    # Parse cron expression (5 fields: minute hour day month day_of_week)
    cron_parts = settings.scheduler_cron.split()
    if len(cron_parts) != 5:
        logger.error("Invalid cron expression: %s", settings.scheduler_cron)
        return

    trigger = CronTrigger(
        minute=cron_parts[0],
        hour=cron_parts[1],
        day=cron_parts[2],
        month=cron_parts[3],
        day_of_week=cron_parts[4],
    )

    _scheduler.add_job(
        run_weekly_analysis,
        trigger=trigger,
        id="weekly_health_analysis",
        name="Weekly Project Health Analysis",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started with cron: %s", settings.scheduler_cron)


def stop_scheduler() -> None:
    """Stop the APScheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")

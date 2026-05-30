"""
APScheduler integration for automated job scraping.

Schedules:
  - Tier 1 scrapers: runs daily at SCRAPER_TIER1_SCHEDULE_HOUR (default: 2 AM)
  - Tier 2 scrapers: runs weekly on Sunday at SCRAPER_TIER2_SCHEDULE_HOUR (default: 3 AM)

The scheduler starts inside the FastAPI lifespan and runs in the background
within the same process as uvicorn.
"""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.scrapers.tier1.h1bgrader import H1BGraderScraper
from app.scrapers.tier1.h1base import H1BaseScraper
from app.scrapers.tier1.visasponsor import VisaSponsorJobsScraper
from app.scrapers.tier1.relocate import RelocateMeScraper
from app.scrapers.tier1.globalsponsorhub import GlobalSponsorHubScraper
from app.scrapers.tier1.github_companies import GitHubCompaniesScraper
from app.scrapers.tier2.linkedin import LinkedInScraper
from app.scrapers.tier2.indeed import IndeedScraper
from app.scrapers.tier2.glassdoor import GlassdoorScraper

logger = logging.getLogger(__name__)

# ── Global scheduler instance ───────────────────────────────────────────
scheduler = AsyncIOScheduler()


def register_jobs():
    """
    Register all scraper jobs with the scheduler.

    Tier 1 (permitted sources) — daily
    Tier 2 (risky sources) — weekly on Sunday

    Each job runs the scraper's `run()` method inside an async task.
    """
    # ── Tier 1 — Daily ──────────────────────────────────────────────────
    tier1_hour = settings.SCRAPER_TIER1_SCHEDULE_HOUR

    scheduler.add_job(
        _run_scraper,
        trigger=CronTrigger(hour=tier1_hour, minute=0),
        args=[H1BGraderScraper()],
        id="scraper_h1bgrader",
        replace_existing=True,
        name="H1BGrader Scraper (Tier 1 — daily)",
    )

    scheduler.add_job(
        _run_scraper,
        trigger=CronTrigger(hour=tier1_hour, minute=15),
        args=[H1BaseScraper()],
        id="scraper_h1base",
        replace_existing=True,
        name="H1Base Scraper (Tier 1 — daily)",
    )

    scheduler.add_job(
        _run_scraper,
        trigger=CronTrigger(hour=tier1_hour, minute=30),
        args=[VisaSponsorJobsScraper()],
        id="scraper_visasponsor",
        replace_existing=True,
        name="VisaSponsorJobs Scraper (Tier 1 — daily)",
    )

    scheduler.add_job(
        _run_scraper,
        trigger=CronTrigger(hour=tier1_hour, minute=45),
        args=[RelocateMeScraper()],
        id="scraper_relocate",
        replace_existing=True,
        name="RelocateMe Scraper (Tier 1 — daily)",
    )

    scheduler.add_job(
        _run_scraper,
        trigger=CronTrigger(hour=tier1_hour, minute=10),
        args=[GlobalSponsorHubScraper()],
        id="scraper_globalsponsorhub",
        replace_existing=True,
        name="GlobalSponsorHub Scraper (Tier 1 — daily)",
    )

    scheduler.add_job(
        _run_scraper,
        trigger=CronTrigger(hour=tier1_hour, minute=20),
        args=[GitHubCompaniesScraper()],
        id="scraper_github_companies",
        replace_existing=True,
        name="GitHub Companies Scraper (Tier 1 — daily)",
    )

    # ── Tier 2 — Weekly (Sunday) ───────────────────────────────────────
    # Disabled by default (SCRAPER_TIER2_ENABLED=False).
    # Set SCRAPER_TIER2_ENABLED=true in production to activate.
    tier2_hour = settings.SCRAPER_TIER2_SCHEDULE_HOUR

    if settings.SCRAPER_TIER2_ENABLED:
        scheduler.add_job(
            _run_scraper,
            trigger=CronTrigger(day_of_week="sun", hour=tier2_hour, minute=0),
            args=[LinkedInScraper()],
            id="scraper_linkedin",
            replace_existing=True,
            name="LinkedIn Scraper (Tier 2 — weekly)",
        )

        scheduler.add_job(
            _run_scraper,
            trigger=CronTrigger(day_of_week="sun", hour=tier2_hour, minute=20),
            args=[IndeedScraper()],
            id="scraper_indeed",
            replace_existing=True,
            name="Indeed Scraper (Tier 2 — weekly)",
        )

        scheduler.add_job(
            _run_scraper,
            trigger=CronTrigger(day_of_week="sun", hour=tier2_hour, minute=40),
            args=[GlassdoorScraper()],
            id="scraper_glassdoor",
            replace_existing=True,
            name="Glassdoor Scraper (Tier 2 — weekly)",
        )

        logger.info(
            "Registered %d scraper jobs (Tier 1: daily at %d:00, Tier 2: Sunday at %d:00)",
            len(scheduler.get_jobs()),
            tier1_hour,
            tier2_hour,
        )
    else:
        logger.info(
            "Registered %d scraper jobs (Tier 1 only — Tier 2 disabled, set SCRAPER_TIER2_ENABLED=true to enable)",
            len(scheduler.get_jobs()),
        )


async def run_scrapers_tier1():
    """
    Manually trigger all Tier 1 scrapers immediately.
    Exposed via POST /api/scrape/trigger for ad-hoc runs.
    """
    logger.info("Manual trigger: running all Tier 1 scrapers")
    scrapers = [
        H1BGraderScraper(),
        H1BaseScraper(),
        VisaSponsorJobsScraper(),
        RelocateMeScraper(),
        GlobalSponsorHubScraper(),
        GitHubCompaniesScraper(),
    ]
    results = []
    for scraper in scrapers:
        result = await scraper.run()
        results.append(result)
    return results


async def _run_scraper(scraper):
    """
    Execute a scraper's run() method in an async task.

    This is the callback called by APScheduler for each scheduled job.
    """
    logger.info("Scheduler triggered: %s", scraper.source)
    try:
        result = await scraper.run()
        logger.info(
            "Scraper '%s' finished: %s (%d jobs)",
            scraper.source, result["status"], result["jobs_found"],
        )
    except Exception as e:
        logger.exception("Scraper '%s' threw unhandled exception: %s", scraper.source, e)


def start_scheduler():
    """
    Start the APScheduler. Called during FastAPI lifespan startup.

    Safe to call multiple times — only starts if not already running.
    """
    if scheduler.running:
        logger.warning("Scheduler is already running")
        return

    register_jobs()
    scheduler.start()
    logger.info("APScheduler started successfully")


def stop_scheduler():
    """
    Gracefully stop the APScheduler. Called during FastAPI lifespan shutdown.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")

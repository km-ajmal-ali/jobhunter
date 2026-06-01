"""
Base scraper framework for JobHunter.

All scrapers inherit from BaseScraper, which provides:
  - HTTP client with configurable timeouts
  - User-agent rotation via fake-useragent
  - Automatic request delays (for Tier 2, randomised between min/max)
  - Database save logic with upsert deduplication
  - ScrapeLog creation and status tracking
"""
from __future__ import annotations

import time
import logging
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import httpx
from fake_useragent import UserAgent
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import pycountry

from app.config import settings
from app.database import AsyncSessionLocal
from app.location_utils import normalize_location
from app.models import Job, Location, Country, ScrapeLog, ScrapeStatus, ScrapeTier

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all job scrapers.

    Subclasses must implement:
      - source: unique string identifier
      - tier: ScrapeTier enum
      - fetch(): retrieve raw HTML/data from the source
      - parse(raw_data): extract job listings into dicts
    """

    # ── Subclass required attributes ───────────────────────────────────
    source: str
    """Unique identifier for this scrape source (e.g. 'linkedin')."""
    tier: ScrapeTier
    """Which tier this source belongs to."""

    def __init__(self):
        self.ua = UserAgent(browsers=["chrome", "firefox", "edge"])
        """Rotating user-agent generator."""
        self.session: httpx.AsyncClient | None = None
        """HTTP client session — initialised in _get_session()."""

    # ── Abstract methods ───────────────────────────────────────────────

    @abstractmethod
    async def fetch(self) -> Any:
        """
        Fetch raw data from the source.

        Returns:
            Raw response (HTML string, JSON dict, etc.)
        """
        ...

    @abstractmethod
    async def parse(self, raw_data: Any) -> list[dict]:
        """
        Parse raw data into a list of job record dicts.

        Each dict must contain:
          - title, company, source_url
          - Optional: location, description, salary_range, posted_at,
                      company_url, visa_sponsorship

        Args:
            raw_data: The output of fetch().

        Returns:
            List of job dicts ready for database insertion.
        """
        ...

    # ── HTTP helpers ───────────────────────────────────────────────────

    async def _get_session(self) -> httpx.AsyncClient:
        """
        Get or create the HTTP client session.

        Rotates user-agent per request and applies proxy config.
        """
        if self.session is None:
            proxies = None
            if settings.PROXY_LIST:
                proxy_list = [p.strip() for p in settings.PROXY_LIST.split(",") if p.strip()]
                if proxy_list:
                    proxies = random.choice(proxy_list)

            self.session = httpx.AsyncClient(
                timeout=settings.SCRAPER_TIMEOUT,
                proxies=proxies,
                follow_redirects=True,
            )
        return self.session

    async def _request(self, url: str, **kwargs) -> httpx.Response:
        """
        Make an HTTP GET request with user-agent rotation and optional delay.

        For Tier 2 scrapers, a random delay is applied before the request
        to reduce the chance of rate-limiting.
        """
        if self.tier == ScrapeTier.TIER2:
            delay = random.uniform(settings.SCRAPER_DELAY_MIN, settings.SCRAPER_DELAY_MAX)
            logger.debug("Tier 2 delay: %.2fs for %s", delay, url)
            time.sleep(delay)

        session = await self._get_session()
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", self.ua.random)
        headers.setdefault("Accept-Language", "en-US,en;q=0.9")

        return await session.get(url, headers=headers, **kwargs)

    async def _close_session(self):
        """Close the HTTP client session if open."""
        if self.session:
            await self.session.aclose()
            self.session = None

    # ── Database helpers ───────────────────────────────────────────────

    async def save_jobs(self, jobs_data: list[dict], db: AsyncSession) -> tuple[int, int]:
        """
        Insert or update job records in the database.

        Uses upsert logic based on (source, source_url) uniqueness constraint.
        Jobs that already exist will have their fields updated.

        Args:
            jobs_data: List of job dicts from parse().
            db: Active database session.

        Returns:
            Tuple of (total_found, total_new).
        """
        total_new = 0
        for data in jobs_data:
            data["source"] = self.source
            data["tier"] = self.tier
            data["scraped_at"] = datetime.now(timezone.utc)
            data["country_code"] = normalize_location(data.get("location"))

            # Check if job already exists
            result = await db.execute(
                select(Job).where(
                    Job.source == self.source,
                    Job.source_url == data["source_url"],
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                for key, value in data.items():
                    setattr(existing, key, value)
            else:
                # Insert new record
                db.add(Job(**data))
                total_new += 1

        return len(jobs_data), total_new

    async def log_result(
        self,
        db: AsyncSession,
        status: ScrapeStatus,
        jobs_found: int = 0,
        jobs_new: int = 0,
        error_msg: str | None = None,
        duration: float | None = None,
    ):
        """
        Create a ScrapeLog entry for this scrape run.

        Args:
            db: Active database session.
            status: Success or failure.
            jobs_found: Total jobs retrieved.
            jobs_new: Jobs that were newly inserted.
            error_msg: Error details if failed.
            duration: How long the scrape took in seconds.
        """
        log_entry = ScrapeLog(
            source=self.source,
            tier=self.tier,
            status=status,
            jobs_found=jobs_found,
            jobs_new=jobs_new,
            error_msg=error_msg,
            duration_seconds=duration,
        )
        db.add(log_entry)

    # ── Stale job cleanup ───────────────────────────────────────────────

    async def deactivate_stale_jobs(
        self,
        active_by_source: dict[str, set[str]],
        db: AsyncSession,
    ):
        """
        Deactivate jobs that no longer appear in the latest scrape.

        For each source, any active job whose source_url is not in the
        current batch gets marked as is_active=False.

        Args:
            active_by_source: Mapping of source -> set of active source_urls.
            db: Active database session.
        """
        for source, active_urls in active_by_source.items():
            if not active_urls:
                continue
            result = await db.execute(
                select(Job).where(
                    Job.source == source,
                    Job.is_active == True,
                    Job.source_url.notin_(active_urls),
                )
            )
            stale = result.scalars().all()
            for job in stale:
                job.is_active = False
            if stale:
                logger.info(
                    "Deactivated %d stale jobs from %s", len(stale), source,
                )

    # ── Location sync ──────────────────────────────────────────────────

    async def sync_locations(self, db: AsyncSession):
        """
        Refresh the locations lookup table from active jobs.
        Removes stale locations and inserts new ones.
        """
        await db.execute(Location.__table__.delete())
        result = await db.execute(
            select(Job.location, func.count(Job.id))
            .where(
                Job.is_active == True,
                Job.location.isnot(None),
                Job.location != "",
            )
            .group_by(Job.location)
            .order_by(Job.location)
        )
        rows = result.all()
        for name, count in rows:
            db.add(Location(name=name, job_count=count))

    # ── Country sync ──────────────────────────────────────────────────

    async def sync_countries(self, db: AsyncSession):
        """
        Refresh the countries lookup table from active jobs.
        """
        await db.execute(Country.__table__.delete())
        result = await db.execute(
            select(Job.country_code, func.count(Job.id))
            .where(
                Job.is_active == True,
                Job.country_code.isnot(None),
                Job.country_code != "",
            )
            .group_by(Job.country_code)
            .order_by(func.count(Job.id).desc())
        )
        rows = result.all()
        for code, count in rows:
            try:
                country = pycountry.countries.lookup(code)
                name = country.name
            except LookupError:
                name = code
            db.add(Country(code=code, name=name, job_count=count))

    # ── Main run method ────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, ConnectionError)),
    )
    async def run(self) -> dict:
        """
        Execute the full scrape pipeline: fetch → parse → save → log.

        Returns a summary dict with results for the scheduler.

        Returns:
            {
                "source": str,
                "status": "success" | "failed",
                "jobs_found": int,
                "jobs_new": int,
                "error": str | None,
                "duration": float,
            }
        """
        start_time = time.time()
        summary = {
            "source": self.source,
            "status": "failed",
            "jobs_found": 0,
            "jobs_new": 0,
            "error": None,
            "duration": 0.0,
        }

        try:
            # Create a dedicated session for this scrape run
            async with AsyncSessionLocal() as db:
                logger.info("Starting scrape: %s", self.source)

                raw_data = await self.fetch()
                jobs_data = await self.parse(raw_data)

                # Collect active URLs before save_jobs modifies the data.
                # jobs_data may be a list[dict] (base) or dict[str, list[dict]] (GH Companies).
                active_by_source: dict[str, set[str]] = {}
                if isinstance(jobs_data, dict):
                    for source, job_list in jobs_data.items():
                        urls = {j.get("source_url") for j in job_list if j.get("source_url")}
                        if urls:
                            active_by_source[source] = urls
                else:
                    urls = {j.get("source_url") for j in jobs_data if j.get("source_url")}
                    if urls:
                        active_by_source[self.source] = urls

                jobs_found, jobs_new = await self.save_jobs(jobs_data, db)

                # Deactivate jobs that disappeared from the source
                await self.deactivate_stale_jobs(active_by_source, db)

                duration = time.time() - start_time
                await self.log_result(
                    db, ScrapeStatus.SUCCESS,
                    jobs_found=jobs_found,
                    jobs_new=jobs_new,
                    duration=duration,
                )
                await db.commit()

                # Refresh lookup tables
                await self.sync_locations(db)
                await self.sync_countries(db)
                await db.commit()

                logger.info(
                    "Scrape complete: %s — %d found, %d new (%.1fs)",
                    self.source, jobs_found, jobs_new, duration,
                )

                summary.update({
                    "status": "success",
                    "jobs_found": jobs_found,
                    "jobs_new": jobs_new,
                    "duration": duration,
                })

        except Exception as e:
            duration = time.time() - start_time
            logger.exception("Scrape failed: %s — %s", self.source, str(e))

            # Log failure
            try:
                async with AsyncSessionLocal() as db:
                    await self.log_result(
                        db, ScrapeStatus.FAILED,
                        error_msg=str(e),
                        duration=duration,
                    )
                    await db.commit()
            except Exception as log_error:
                logger.error("Failed to log scrape result: %s", log_error)

            summary.update({
                "status": "failed",
                "error": str(e),
                "duration": duration,
            })

        finally:
            await self._close_session()

        return summary

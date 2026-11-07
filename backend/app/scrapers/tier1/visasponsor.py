"""
VisaSponsorJobs scraper (Tier 1 — public job board).

Scrapes job listings from visasponsor.jobs which aggregates
visa sponsorship job postings globally. This source is
accessible and does not block programmatic requests.

/api/jobs returns JSON (paginated: {"data": [...], "total", "page",
"page_size"}), not HTML — job detail pages live at /job/{slug}.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.models import ScrapeTier
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class VisaSponsorJobsScraper(BaseScraper):
    """Scraper for visasponsor.jobs job listings."""

    source = "visasponsor"
    tier = ScrapeTier.TIER1

    BASE_URL = "https://visasponsor.jobs"
    SEARCH_URL = f"{BASE_URL}/api/jobs"

    async def fetch(self) -> list[dict]:
        """
        Fetch job listing pages from the visasponsor.jobs JSON API.

        Scrapes the first 3 pages to get ~90 job listings.
        """
        all_items: list[dict] = []
        for page in range(0, 3):
            url = f"{self.SEARCH_URL}?page={page}"
            response = await self._request(url)
            try:
                data = response.json()
            except ValueError as e:
                logger.warning("VisaSponsorJobs page %d: non-JSON response: %s", page, e)
                continue
            all_items.extend(data.get("data", []))

            await asyncio.sleep(1.5)

        return all_items

    async def parse(self, raw_data: list[dict]) -> list[dict]:
        """
        Parse visasponsor.jobs API job objects into job record dicts.
        """
        jobs = []

        for item in raw_data:
            try:
                slug = item.get("slug")
                title = (item.get("title") or "").strip()
                if not slug or not title:
                    continue

                source_url = f"{self.BASE_URL}/job/{slug}"
                company = item.get("company_name") or "Unknown"

                location_parts = [
                    p for p in (item.get("city"), item.get("state"), item.get("country")) if p
                ]
                location = ", ".join(location_parts) if location_parts else None

                tags = item.get("visa_type") or ["H-1B"]
                salary_range = item.get("salary")

                posted_at = None
                published = item.get("published_at")
                if published:
                    try:
                        posted_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        posted_at = datetime.now(timezone.utc)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "source_url": source_url,
                    "tags": tags,
                    "description": None,
                    "salary_range": salary_range,
                    "posted_at": posted_at,
                    "visa_sponsorship": True,
                })

            except Exception as e:
                logger.warning("Error parsing VisaSponsorJobs item: %s", e)
                continue

        return jobs

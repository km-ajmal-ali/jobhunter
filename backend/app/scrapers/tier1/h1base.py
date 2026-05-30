"""
H1Base scraper (Tier 1 — permitted source).

Scrapes job listings from h1base.com which tracks
H1B visa sponsorship and green card job postings.

This source is considered low-risk (public visa database).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from app.models import ScrapeTier
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class H1BaseScraper(BaseScraper):
    """Scraper for h1base.com job listings."""

    source = "h1base"
    tier = ScrapeTier.TIER1

    BASE_URL = "https://www.h1base.com"
    SEARCH_URL = f"{BASE_URL}/jobs"

    async def fetch(self) -> str:
        """
        Fetch the H1Base jobs listing page.

        Returns:
            HTML string of the search results page.
        """
        response = await self._request(self.SEARCH_URL)
        return response.text

    async def parse(self, raw_data: str) -> list[dict]:
        """
        Parse H1Base HTML into job record dicts.

        Args:
            raw_data: HTML from the fetch step.

        Returns:
            List of job dicts for database insertion.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # H1Base typically uses table rows or listing divs
        # Adjust selectors based on actual page structure
        rows = soup.select("table.job-list tr, .job-row, .job-item, div[class*='job']")

        for row in rows:
            try:
                # Title and URL
                title_el = row.select_one(
                    "a[href*='/job/'], a[href*='/jobs/'], .job-title a"
                )
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                source_url = title_el.get("href", "")
                if source_url and not source_url.startswith("http"):
                    source_url = f"{self.BASE_URL}{source_url}"

                # Company
                company_el = row.select_one(
                    ".company, .employer, [class*='company'], td:nth-child(2)"
                )
                company = company_el.get_text(strip=True) if company_el else "Unknown"

                # Location
                location_el = row.select_one(
                    ".location, .job-location, [class*='location'], td:nth-child(3)"
                )
                location = location_el.get_text(strip=True) if location_el else None

                # Description
                desc_el = row.select_one(
                    ".description, .job-description, [class*='description']"
                )
                description = desc_el.get_text(strip=True) if desc_el else None

                # Salary
                salary_el = row.select_one(
                    ".salary, .pay-range, [class*='salary'], td:nth-child(4)"
                )
                salary_range = salary_el.get_text(strip=True) if salary_el else None

                # Posted date
                date_el = row.select_one(
                    ".date, .posted-date, time, td:nth-child(5)"
                )
                posted_at = None
                if date_el:
                    date_text = date_el.get("datetime") or date_el.get_text(strip=True)
                    if date_text:
                        try:
                            posted_at = datetime.fromisoformat(date_text)
                        except (ValueError, TypeError):
                            posted_at = datetime.now(timezone.utc)

                # Company website
                company_link_el = row.select_one(
                    "a[href*='.com']:not([href*='/job/']):not([href*='/jobs/'])"
                )
                company_url = company_link_el.get("href") if company_link_el else None

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "source_url": source_url,
                    "company_url": company_url,
                    "description": description,
                    "salary_range": salary_range,
                    "posted_at": posted_at,
                    "visa_sponsorship": True,
                })

            except Exception as e:
                logger.warning("Error parsing H1Base row: %s", e)
                continue

        return jobs

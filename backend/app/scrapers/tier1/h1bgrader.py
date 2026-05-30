"""
H1BGrader scraper (Tier 1 — permitted source).

Scrapes job listings from h1bgrader.com which aggregates
H1B visa sponsorship job postings.

This source is considered low-risk (public job board).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from app.models import ScrapeTier
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class H1BGraderScraper(BaseScraper):
    """Scraper for h1bgrader.com job listings."""

    source = "h1bgrader"
    tier = ScrapeTier.TIER1

    BASE_URL = "https://h1bgrader.com"
    SEARCH_URL = f"{BASE_URL}/jobs"

    async def fetch(self) -> str:
        """
        Fetch the H1BGrader jobs listing page.

        Returns:
            HTML string of the search results page.
        """
        # Fetch first 2 pages to get enough listings
        all_html = ""
        for page in range(1, 3):
            url = f"{self.SEARCH_URL}?page={page}"
            response = await self._request(url)
            all_html += response.text

            # Brief delay between pages
            import asyncio
            await asyncio.sleep(1.5)

        return all_html

    async def parse(self, raw_data: str) -> list[dict]:
        """
        Parse H1BGrader HTML into job record dicts.

        Args:
            raw_data: Combined HTML from the fetch step.

        Returns:
            List of job dicts for database insertion.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # H1BGrader job cards are typically in <div class="job-card"> elements
        # Adjust selectors based on actual page structure
        job_cards = soup.select("div.job-card, div.job-listing, div[class*='job']")

        for card in job_cards:
            try:
                # Title
                title_el = card.select_one("h2 a, h3 a, .job-title a, a[href*='/jobs/']")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                source_url = title_el.get("href", "")
                if source_url and not source_url.startswith("http"):
                    source_url = f"{self.BASE_URL}{source_url}"

                # Company
                company_el = card.select_one(".company, .company-name, [class*='company']")
                company = company_el.get_text(strip=True) if company_el else "Unknown"

                # Location
                location_el = card.select_one(".location, .job-location, [class*='location']")
                location = location_el.get_text(strip=True) if location_el else None

                # Description snippet
                desc_el = card.select_one(".description, .job-description, p")
                description = desc_el.get_text(strip=True) if desc_el else None

                # Salary
                salary_el = card.select_one(".salary, .pay, [class*='salary']")
                salary_range = salary_el.get_text(strip=True) if salary_el else None

                # Company URL
                company_link_el = card.select_one("a[href*='.com'], a[href*='http']")
                company_url = None
                if company_link_el:
                    href = company_link_el.get("href", "")
                    if href.startswith("http") and "/jobs/" not in href:
                        company_url = href

                # Posted date
                date_el = card.select_one(".date, .posted-date, time")
                posted_at = None
                if date_el:
                    date_text = date_el.get("datetime") or date_el.get_text(strip=True)
                    if date_text:
                        try:
                            posted_at = datetime.fromisoformat(date_text)
                        except (ValueError, TypeError):
                            posted_at = datetime.now(timezone.utc)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "source_url": source_url,
                    "company_url": company_url,
                    "description": description,
                    "salary_range": salary_range,
                    "posted_at": posted_at,
                    "visa_sponsorship": True,  # H1BGrader is visa-specific
                })

            except Exception as e:
                logger.warning("Error parsing H1BGrader card: %s", e)
                continue

        return jobs

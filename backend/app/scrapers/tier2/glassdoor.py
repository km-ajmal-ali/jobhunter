"""
Glassdoor job scraper (Tier 2 — risky / ToS-restricted).

Scrapes Glassdoor job search results for visa-sponsorship keywords.

⚠️  Glassdoor prohibits scraping. Use randomised delays and UA rotation.
     Use at your own risk. Runs weekly (Sundays).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from app.models import ScrapeTier
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class GlassdoorScraper(BaseScraper):
    """Scraper for glassdoor.com job listings."""

    source = "glassdoor"
    tier = ScrapeTier.TIER2

    BASE_URL = "https://www.glassdoor.com"

    SEARCH_QUERIES = [
        "visa sponsorship",
        "h1b visa",
        "work visa",
    ]

    async def fetch(self) -> str:
        """
        Fetch Glassdoor search results for each query.

        Returns:
            Combined HTML from all queries.
        """
        all_html = ""

        for query in self.SEARCH_QUERIES:
            params = {
                "keyword": query,
                "location": "United States",
            }
            url = f"{self.BASE_URL}/Job/jobs.htm?{urlencode(params)}"

            try:
                response = await self._request(url)
                all_html += response.text

                import asyncio
                await asyncio.sleep(4)  # Glassdoor is aggressive with rate limiting
            except Exception as e:
                logger.warning("Glassdoor query '%s' failed: %s", query, e)
                continue

        return all_html

    async def parse(self, raw_data: str) -> list[dict]:
        """
        Parse Glassdoor search results HTML into job dicts.

        Glassdoor heavily relies on JavaScript rendering, so server-side
        HTML will be limited. This parser extracts what's available.

        Args:
            raw_data: Combined HTML from fetch.

        Returns:
            List of job dicts for database insertion.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []
        seen_urls = set()

        # Glassdoor job card selectors
        job_cards = soup.select(
            "li.react-job-listing, "
            "div.jobContainer, "
            "div[class*='jobListing'], "
            "a[href*='/partner/jobListing']"
        )

        for card in job_cards:
            try:
                # Title and URL
                title_el = card.select_one(
                    "a.jobLink, "
                    "a[class*='job-title'], "
                    "a[href*='/job-listing/'], "
                    "strong a"
                )
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")

                source_url = (
                    f"{self.BASE_URL}{href}" if href.startswith("/") else href
                )

                if source_url in seen_urls:
                    continue
                seen_urls.add(source_url)

                # Company
                company_el = card.select_one(
                    "div.employerName, "
                    "[class*='employer'], "
                    "[class*='company'], "
                    "span[class*='emp']"
                )
                company = company_el.get_text(strip=True) if company_el else "Unknown"

                # Location
                location_el = card.select_one(
                    "div.location, "
                    "[class*='location'], "
                    "span[class*='loc']"
                )
                location = location_el.get_text(strip=True) if location_el else None

                # Salary estimate
                salary_el = card.select_one(
                    "span.estimate, "
                    "[class*='salary'], "
                    "[class*='pay']"
                )
                salary_range = salary_el.get_text(strip=True) if salary_el else None

                # Company URL
                company_link = card.select_one("a[href*='.com']:not([href*='/job/'])")
                company_url = None
                if company_link:
                    cu = company_link.get("href", "")
                    if cu.startswith("http"):
                        company_url = cu

                # Posted date
                date_el = card.select_one(
                    "div.age, span.age, [class*='date'], [class*='age']"
                )
                posted_at = None
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    if "today" in date_text.lower():
                        posted_at = datetime.now(timezone.utc)
                    elif "day" in date_text.lower():
                        try:
                            import re
                            days = int(re.search(r"(\d+)", date_text).group(1))
                            posted_at = datetime.now(timezone.utc)
                        except Exception:
                            posted_at = datetime.now(timezone.utc)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "source_url": source_url,
                    "company_url": company_url,
                    "description": None,
                    "salary_range": salary_range,
                    "posted_at": posted_at,
                    "visa_sponsorship": True,
                })

            except Exception as e:
                logger.warning("Error parsing Glassdoor card: %s", e)
                continue

        return jobs

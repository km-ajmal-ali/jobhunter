"""
LinkedIn job scraper (Tier 2 — risky / ToS-restricted).

Scrapes LinkedIn job search results for visa-sponsorship-related keywords.

⚠️  LinkedIn strictly prohibits scraping in its User Agreement.
     This scraper uses randomised delays and user-agent rotation
     to minimise detection, but use at your own risk.

     This runs weekly (Sundays) per the two-tier schedule.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from app.models import ScrapeTier
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn job search results."""

    source = "linkedin"
    tier = ScrapeTier.TIER2

    BASE_URL = "https://www.linkedin.com"

    # Search for jobs with visa-sponsorship keywords
    SEARCH_QUERIES = [
        "visa sponsorship",
        "h1b visa",
        "h1b sponsorship",
        "visa sponsor",
        "work visa",
    ]

    async def fetch(self) -> str:
        """
        Fetch LinkedIn job search results for each query.

        Returns:
            Combined HTML from all search queries.
        """
        all_html = ""

        for query in self.SEARCH_QUERIES:
            # LinkedIn job search URL format
            encoded_query = query.replace(" ", "%20")
            url = (
                f"{self.BASE_URL}/jobs/search/"
                f"?keywords={encoded_query}"
                f"&location=United%20States"
                f"&trk=public_jobs_jobs-search-bar_search-submit"
                f"&position=1&pageNum=0"
            )

            try:
                response = await self._request(url)
                all_html += response.text

                import asyncio
                await asyncio.sleep(3)  # Extra delay between queries
            except Exception as e:
                logger.warning("LinkedIn search query '%s' failed: %s", query, e)
                continue

        return all_html

    async def parse(self, raw_data: str) -> list[dict]:
        """
        Parse LinkedIn search results HTML into job dicts.

        LinkedIn uses client-side rendering, so we may get limited results
        from server-rendered HTML. This parser extracts what's available.

        Args:
            raw_data: Combined HTML from fetch.

        Returns:
            List of job dicts for database insertion.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []
        seen_urls = set()

        # LinkedIn job cards in search results
        # These selectors may need updating as LinkedIn's DOM changes
        job_cards = soup.select(
            "li[data-occludable-job-id], "
            "div.job-card-container, "
            "a[href*='/jobs/view/'], "
            "div[class*='job-search-card']"
        )

        for card in job_cards:
            try:
                # Extract job ID or URL
                link = card if card.name == "a" else card.select_one("a[href*='/jobs/view/']")
                if not link:
                    continue

                href = link.get("href", "")
                if not href.startswith("http"):
                    href = f"{self.BASE_URL}{href}"

                # Deduplicate
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # Title
                title_el = card.select_one(
                    "h3, .job-title, [class*='title'], [class*='job-title']"
                )
                title = title_el.get_text(strip=True) if title_el else "Unknown"

                # Company
                company_el = card.select_one(
                    "h4, .company-name, [class*='company'], [class*='employer']"
                )
                company = company_el.get_text(strip=True) if company_el else "Unknown"

                # Location
                location_el = card.select_one(
                    ".job-location, [class*='location'], span[class*='location']"
                )
                location = location_el.get_text(strip=True) if location_el else None

                # Extract company URL from LinkedIn company page link
                company_link = card.select_one("a[href*='/company/']")
                company_url = None
                if company_link:
                    company_url = (
                        f"{self.BASE_URL}{company_link['href']}"
                        if company_link["href"].startswith("/")
                        else company_link["href"]
                    )

                # Posted date
                date_el = card.select_one("time, [class*='date'], [class*='posted']")
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
                    "source_url": href.split("?")[0],  # Clean URL
                    "company_url": company_url,
                    "description": None,  # Full description requires detail page
                    "salary_range": None,
                    "posted_at": posted_at,
                    "visa_sponsorship": True,
                })

            except Exception as e:
                logger.warning("Error parsing LinkedIn card: %s", e)
                continue

        return jobs

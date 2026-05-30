"""
Indeed job scraper (Tier 2 — risky / ToS-restricted).

Scrapes Indeed job search results for visa-sponsorship-related keywords.

⚠️  Indeed prohibits scraping in its terms of service.
     This scraper uses randomised delays and user-agent rotation.
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


class IndeedScraper(BaseScraper):
    """Scraper for indeed.com job search results."""

    source = "indeed"
    tier = ScrapeTier.TIER2

    BASE_URL = "https://www.indeed.com"

    SEARCH_QUERIES = [
        "visa sponsorship",
        "h1b visa",
        "h1b sponsorship",
        "work visa sponsor",
    ]

    async def fetch(self) -> str:
        """
        Fetch Indeed search results for each query.

        Returns:
            Combined HTML from all queries and pages.
        """
        all_html = ""

        for query in self.SEARCH_QUERIES:
            for page in range(2):  # First 2 pages per query
                params = {
                    "q": query,
                    "l": "United States",
                    "start": page * 10,
                }
                url = f"{self.BASE_URL}/jobs?{urlencode(params)}"

                try:
                    response = await self._request(url)
                    all_html += response.text

                    import asyncio
                    await asyncio.sleep(4)  # Extra delay for Indeed
                except Exception as e:
                    logger.warning("Indeed query '%s' page %d failed: %s", query, page, e)
                    continue

        return all_html

    async def parse(self, raw_data: str) -> list[dict]:
        """
        Parse Indeed search result HTML into job dicts.

        Args:
            raw_data: Combined HTML from fetch.

        Returns:
            List of job dicts for database insertion.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []
        seen_urls = set()

        # Indeed uses various card selectors — try common patterns
        job_cards = soup.select(
            "div.job_seen_beacon, "
            "div[data-testid='job-card'], "
            "div.jobsearch-SerpJobCard, "
            "div[class*='card']:has(a[href*='/rc/clk'])"
        )

        for card in job_cards:
            try:
                # Job title and URL
                title_el = card.select_one(
                    "h2.jobTitle a, "
                    "a[data-jk], "
                    "a[id*='job_'], "
                    "a.jobtitle"
                )
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                job_id = title_el.get("data-jk") or ""
                href = title_el.get("href", "")

                # Build Indeed-specific job URL
                if job_id:
                    source_url = f"{self.BASE_URL}/viewjob?jk={job_id}"
                elif href:
                    source_url = (
                        f"{self.BASE_URL}{href}" if href.startswith("/") else href
                    )
                else:
                    continue

                # Deduplicate
                if source_url in seen_urls:
                    continue
                seen_urls.add(source_url)

                # Company name
                company_el = card.select_one(
                    "span.companyName, "
                    "[data-testid='company-name'], "
                    ".company, "
                    "span[class*='company']"
                )
                company = company_el.get_text(strip=True) if company_el else "Unknown"

                # Location
                location_el = card.select_one(
                    "div.companyLocation, "
                    "[data-testid='text-location'], "
                    ".location, "
                    "span[class*='location']"
                )
                location = location_el.get_text(strip=True) if location_el else None

                # Salary
                salary_el = card.select_one(
                    ".salary-snippet-container, "
                    "[data-testid='attribute_snippet_testid'], "
                    ".salary, "
                    ".salaryText"
                )
                salary_range = salary_el.get_text(strip=True) if salary_el else None

                # Posted date
                date_el = card.select_one(
                    ".date, span.date, [class*='date'], [class*='posted']"
                )
                posted_at = None
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    # Indeed shows relative dates ("30+ days ago"), convert if possible
                    if "today" in date_text.lower():
                        posted_at = datetime.now(timezone.utc)
                    elif "day" in date_text.lower():
                        try:
                            days = int(re.search(r"(\d+)", date_text).group(1))
                            posted_at = datetime.now(timezone.utc)
                        except Exception:
                            posted_at = datetime.now(timezone.utc)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "source_url": source_url,
                    "company_url": None,  # Indeed doesn't expose company URL easily
                    "description": None,
                    "salary_range": salary_range,
                    "posted_at": posted_at,
                    "visa_sponsorship": True,
                })

            except Exception as e:
                logger.warning("Error parsing Indeed card: %s", e)
                continue

        return jobs

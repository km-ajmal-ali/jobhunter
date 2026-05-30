"""
Relocate.me scraper (Tier 1 — public job board).

Scrapes job listings from relocate.me which aggregates
international jobs with visa sponsorship and relocation support.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import ClassVar

from bs4 import BeautifulSoup

from app.models import ScrapeTier
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class RelocateMeScraper(BaseScraper):
    """Scraper for relocate.me international job listings."""

    source = "relocate"
    tier = ScrapeTier.TIER1

    BASE_URL: ClassVar = "https://relocate.me"
    SEARCH_URL: ClassVar = f"{BASE_URL}/international-jobs"

    # Job categories to scrape (form checkbox values)
    CATEGORIES: ClassVar = [
        "back-end",
        "data-science",
        "devops-sre",
        "front-end",
        "full-stack",
        "lead-developer",
        "manager",
        "other",
        "qa",
        "security",
    ]

    async def fetch(self) -> str:
        """Fetch all job categories and combine HTML."""
        all_html = ""
        # Fetch base page first (has all jobs without filter)
        response = await self._request(self.SEARCH_URL)
        all_html += response.text

        # Fetch each category page
        for category in self.CATEGORIES:
            url = f"{self.SEARCH_URL}?category%5B%5D={category}"
            response = await self._request(url)
            all_html += response.text
            await asyncio.sleep(1.0)

        return all_html

    async def parse(self, raw_data: str) -> list[dict]:
        """
        Parse relocate.me HTML into job record dicts.

        Job cards are div.jobs-list__job elements containing
        title, company, location, and preview text.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []
        seen_urls = set()

        for card in soup.select(".jobs-list__job"):
            try:
                # Title + URL
                title_el = card.select_one(".job__title a")
                if not title_el:
                    continue
                href = title_el.get("href", "")
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)
                source_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                # Title: <b>Title</b> in City
                title_b = title_el.find("b")
                title = title_b.get_text(strip=True) if title_b else title_el.get_text(strip=True).split("in")[0].strip()

                # Company divs: first is location (country), second is company name
                company_divs = card.select(".job__company p")
                location = None
                company = "Unknown"
                if len(company_divs) >= 1:
                    location = company_divs[0].get_text(strip=True)
                if len(company_divs) >= 2:
                    company = company_divs[1].get_text(strip=True)

                # Extract city from title_el (e.g. "in London")
                title_text = title_el.get_text(strip=True)
                if "in" in title_text:
                    city_part = title_text.split("in")[-1].strip()
                    if city_part and location:
                        location = f"{city_part}, {location}"

                # Description preview
                preview_el = card.select_one(".job__preview")
                description = preview_el.get_text(strip=True) if preview_el else None

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "source_url": source_url,
                    "company_url": None,
                    "description": description,
                    "salary_range": None,
                    "posted_at": datetime.now(timezone.utc),
                    "visa_sponsorship": True,
                })

            except Exception as e:
                logger.warning("Error parsing RelocateMe card: %s", e)
                continue

        return jobs

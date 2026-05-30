"""
GlobalSponsorHub scraper (Tier 1 — public job board).

Scrapes job listings from globalsponsorhub.com.
Note: listing pages are JS-rendered, so job URLs are discovered
via the sitemap.xml. Only jobs present in the sitemap are scraped.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import ClassVar

from bs4 import BeautifulSoup

from app.models import ScrapeTier
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class GlobalSponsorHubScraper(BaseScraper):
    """Scraper for globalsponsorhub.com job listings."""

    source = "globalsponsorhub"
    tier = ScrapeTier.TIER1

    BASE_URL: ClassVar = "https://www.globalsponsorhub.com"
    SITEMAP_URL: ClassVar = f"{BASE_URL}/sitemap.xml"

    async def fetch(self) -> str:
        """Fetch all job detail pages discovered via sitemap."""
        response = await self._request(self.SITEMAP_URL)
        job_urls = re.findall(rf"{re.escape(self.BASE_URL)}/jobs/[a-zA-Z0-9]+", response.text)
        job_urls = list(set(job_urls))
        logger.info("Discovered %d job URLs from sitemap", len(job_urls))

        all_html = ""
        for url in job_urls:
            try:
                resp = await self._request(url)
                all_html += resp.text
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning("Failed to fetch job %s: %s", url, e)

        return all_html

    async def parse(self, raw_data: str) -> list[dict]:
        """
        Parse globalsponsorhub job detail pages into job records.

        Each page contains: title, company, location, description.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []
        # Each page has a <h1> with the job title
        # The structure varies — extract what we can
        seen_titles = set()

        for h1 in soup.find_all("h1"):
            title = h1.get_text(strip=True)
            if not title or title in seen_titles or len(title) < 3:
                continue
            seen_titles.add(title)

            # Find description divs
            desc_div = h1.find_next("div", class_=lambda x: x and "desc" in x.lower())
            description = desc_div.get_text(strip=True) if desc_div else None

            # Company name — try various selectors
            company = "Unknown"
            for sel in ["[class*=company]", "[class*=employer]", "[class*=org]"]:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(strip=True)
                    if txt and len(txt) < 100:
                        company = txt
                        break

            # Location
            location = None
            for sel in ["[class*=location]", "[class*=country]", "[class*=address]"]:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(strip=True)
                    if txt and len(txt) < 200:
                        location = txt
                        break

            # Salary
            salary_range = None
            for sel in ["[class*=salary]", "[class*=pay]", "[class*=compensation]"]:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(strip=True)
                    if txt and len(txt) < 100:
                        salary_range = txt
                        break

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "source_url": "",
                "company_url": None,
                "description": description,
                "salary_range": salary_range,
                "posted_at": datetime.now(timezone.utc),
                "visa_sponsorship": True,
            })

        return jobs

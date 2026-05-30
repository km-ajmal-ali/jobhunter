"""
VisaSponsorJobs scraper (Tier 1 — public job board).

Scrapes job listings from visasponsor.jobs which aggregates
visa sponsorship job postings globally. This source is
accessible and does not block programmatic requests.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.models import ScrapeTier
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class VisaSponsorJobsScraper(BaseScraper):
    """Scraper for visasponsor.jobs job listings."""

    source = "visasponsor"
    tier = ScrapeTier.TIER1

    BASE_URL = "https://visasponsor.jobs"
    SEARCH_URL = f"{BASE_URL}/api/jobs"

    async def fetch(self) -> str:
        """
        Fetch job listing pages from visasponsor.jobs.

        Scrapes the first 3 pages to get ~90 job listings.
        """
        all_html = ""
        for page in range(0, 3):
            url = f"{self.SEARCH_URL}?page={page}"
            response = await self._request(url)
            all_html += response.text

            await asyncio.sleep(1.5)

        return all_html

    async def parse(self, raw_data: str) -> list[dict]:
        """
        Parse visasponsor.jobs HTML into job record dicts.

        Job cards are nested inside <a> elements with hrefs like
        /api/jobs/{uuid}/{slug}. The card contains title, company,
        location, visa type tag, and publish date.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Each job link is an <a> wrapping the card
        job_links = soup.select("a[href*='/api/jobs/']")
        seen_urls = set()

        for link in job_links:
            href = link.get("href", "")
            # Skip pagination and filter links
            if "?" in href or href in seen_urls:
                continue
            seen_urls.add(href)

            source_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            card = link.select_one(".job")
            if not card:
                continue

            try:
                # Title
                title_el = card.select_one(".fs-5")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                # Company
                company_el = card.select_one(".employer-name")
                company = "Unknown"
                if company_el:
                    # Get text without children (in case of "View all jobs" attachments)
                    company = "".join(company_el.find_all(string=True, recursive=False)).strip()
                    if not company:
                        company = company_el.get_text(strip=True)
                    # Clean up any appended garbage text
                    for suffix in ["View all jobs", "View all", "All jobs"]:
                        if company.endswith(suffix):
                            company = company[: -len(suffix)].strip()

                # Location — all spans under the location row
                location_parts = []
                for span in card.select(".row.my-2 .col-11 span"):
                    text = span.get_text(strip=True).strip(",")
                    if text:
                        location_parts.append(text)
                location = ", ".join(location_parts) if location_parts else None

                # Visa type tag
                tag_el = card.select_one(".tag")
                visa_type = tag_el.get_text(strip=True) if tag_el else "H-1B"

                # Publish date
                date_el = card.select_one("div.sub-font span:last-child")
                posted_at = None
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    if date_text:
                        try:
                            posted_at = datetime.strptime(date_text, "%d-%m-%Y").replace(tzinfo=timezone.utc)
                        except (ValueError, TypeError):
                            posted_at = datetime.now(timezone.utc)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "source_url": source_url,
                    "company_url": None,
                    "description": None,
                    "salary_range": None,
                    "posted_at": posted_at,
                    "visa_sponsorship": True,
                })

            except Exception as e:
                logger.warning("Error parsing VisaSponsorJobs card: %s", e)
                continue

        return jobs

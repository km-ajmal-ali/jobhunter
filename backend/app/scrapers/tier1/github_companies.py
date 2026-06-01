"""
GitHub Companies scraper.

Scrapes job listings from visa-sponsorship companies listed in
github.com/shubheksha/companies-sponsoring-visas.

Only companies with a publicly accessible JSON API are scraped:
  - Greenhouse ATS: boards-api.greenhouse.io/v1/boards/{company}/jobs

The remaining companies in the GitHub list use custom career sites
without structured data (no JSON-LD JobPosting schema, no standard
ATS API), which would require per-company custom scrapers.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import ClassVar

from bs4 import BeautifulSoup

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Job, ScrapeTier
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class GitHubCompaniesScraper(BaseScraper):
    """Scraper for GitHub-listed companies that use Greenhouse."""

    source = "github-companies"
    tier = ScrapeTier.TIER1

    # Companies with a working Greenhouse JSON API.
    # slug -> display name mapping.
    GREENHOUSE_COMPANIES: ClassVar[dict[str, str]] = {
        "stripe": "Stripe",
        "monzo": "Monzo",
        "gocardless": "GoCardless",
        "intercom": "Intercom",
        "twilio": "Twilio",
        "datadog": "Datadog",
        "trivago": "Trivago",
        "adyen": "Adyen",
        "skyscanner": "Skyscanner",
        "hellofresh": "HelloFresh",
    }

    async def _fetch_greenhouse(self, slug: str, display_name: str) -> list[dict]:
        """Fetch all jobs for a Greenhouse company via JSON API."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?per_page=500&content=true"
        try:
            resp = await self._request(url)
            data = resp.json()
            jobs = data.get("jobs", [])
            logger.info("Greenhouse[%s]: %d jobs", slug, len(jobs))
            return [
                {
                    "strategy": "greenhouse",
                    "company_name": display_name,
                    "raw": j,
                }
                for j in jobs
            ]
        except Exception as e:
            logger.warning("Greenhouse[%s] failed: %s", slug, e)
            return []

    async def fetch(self) -> dict:
        """Fetch jobs from all Greenhouse companies."""
        results = {}
        for slug, display_name in self.GREENHOUSE_COMPANIES.items():
            results[f"greenhouse_{slug}"] = await self._fetch_greenhouse(slug, display_name)
            await asyncio.sleep(1.0)
        return results

    def _parse_greenhouse(self, raw: dict) -> dict:
        """Parse a single Greenhouse API job object into a job record."""
        data = raw["raw"]
        location = data.get("location", {})
        offices = [o["name"] for o in data.get("offices", [])]
        loc_parts = [location.get("name", "")] if location.get("name") else offices
        location_str = ", ".join(loc_parts) if loc_parts else None
        content = data.get("content", "")
        desc = BeautifulSoup(content, "lxml").get_text(strip=True) if content else None
        updated = data.get("updated_at")
        posted_at = None
        if updated:
            try:
                posted_at = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                posted_at = datetime.now(timezone.utc)
        # Tags from departments + metadata
        tags = []
        for dept in data.get("departments", []):
            name = dept.get("name")
            if name and name not in tags:
                tags.append(name)
        for meta in data.get("metadata", []):
            val = meta.get("value")
            if val and val not in tags:
                tags.append(val)
        # Apply URL: Greenhouse applies at the same URL, but some
        # companies expose a direct apply link in the API.
        apply_url = data.get("apply_url")
        if not apply_url and data.get("absolute_url"):
            apply_url = data["absolute_url"]
        return {
            "title": data.get("title", "Unknown"),
            "company": raw["company_name"],
            "location": location_str,
            "source_url": data.get("absolute_url", ""),
            "apply_url": apply_url,
            "description": desc,
            "tags": tags or None,
            "posted_at": posted_at or datetime.now(timezone.utc),
            "visa_sponsorship": True,
        }

    async def parse(self, raw_data: dict) -> list[dict]:
        """Parse all fetched data into job record dicts."""
        jobs = []
        seen = set()
        for key, items in raw_data.items():
            slug = key.split("_", 1)[1]  # e.g. "greenhouse_stripe" -> "stripe"
            for item in items:
                try:
                    job = self._parse_greenhouse(item)
                    if job["source_url"] and job["source_url"] not in seen:
                        seen.add(job["source_url"])
                        job["_company_slug"] = slug
                        jobs.append(job)
                except Exception as e:
                    logger.warning("Parse error [%s]: %s", key, e)
        # Group by company slug for per-company source labels
        grouped = {}
        for job in jobs:
            slug = job.pop("_company_slug", self.source)
            grouped.setdefault(slug, []).append(job)
        return grouped

    async def save_jobs(self, jobs_data: dict, db: AsyncSession) -> tuple[int, int]:
        """Insert or update per-company job records with company-specific source."""
        total_found = 0
        total_new = 0
        for company_slug, job_list in jobs_data.items():
            for data in job_list:
                data["source"] = company_slug
                data["tier"] = self.tier
                data["scraped_at"] = datetime.now(timezone.utc)
                total_found += 1
                result = await db.execute(
                    select(Job).where(
                        Job.source == data["source"],
                        Job.source_url == data["source_url"],
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    db.add(Job(**data))
                    total_new += 1
        return total_found, total_new

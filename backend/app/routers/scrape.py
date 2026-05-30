"""
Manual scrape trigger endpoint.

Allows ad-hoc execution of Tier 1 scrapers via the API.
Tier 2 scrapers can only be triggered manually if ENABLED in config.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.scrapers.scheduler import run_scrapers_tier1

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


@router.post("/trigger")
async def trigger_scrape():
    """
    Manually trigger all Tier 1 scrapers immediately.

    Useful for testing or forcing an update outside the scheduled window.
    Tier 2 scrapers are excluded (only run on schedule in production).

    Returns a summary of each scraper's result.
    """
    results = await run_scrapers_tier1()
    return {"triggered": True, "results": results}

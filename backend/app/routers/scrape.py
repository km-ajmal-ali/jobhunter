"""
Manual scrape trigger endpoint.

Requires X-API-Key header matching SCRAPE_API_KEY config.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.limiter import limiter
from app.scrapers.scheduler import run_scrapers_tier1

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


@router.post("/trigger")
@limiter.limit("2/hour")
async def trigger_scrape(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
):
    if settings.SCRAPE_API_KEY:
        if not x_api_key or x_api_key != settings.SCRAPE_API_KEY:
            raise HTTPException(status_code=403, detail="Invalid or missing API key")
    results = await run_scrapers_tier1()
    return {"triggered": True, "results": results}

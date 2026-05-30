"""
Manual scrape trigger endpoint.

Requires X-API-Key header matching SCRAPE_API_KEY config.
"""
import logging

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.limiter import limiter
from app.scrapers.scheduler import run_scrapers_tier1

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


@router.post("/trigger")
@limiter.limit("2/hour")
async def trigger_scrape(request: Request):
    api_key = request.headers.get("x-api-key")
    if settings.SCRAPE_API_KEY:
        if not api_key or api_key != settings.SCRAPE_API_KEY:
            raise HTTPException(status_code=403, detail="Invalid or missing API key")
    results = await run_scrapers_tier1()
    return {"triggered": True, "results": results}

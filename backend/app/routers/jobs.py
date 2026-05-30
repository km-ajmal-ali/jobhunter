"""
Job listing API router.

Endpoints:
  - GET /api/jobs       — search / filter / paginate job listings
  - GET /api/jobs/{id}  — single job detail
  - GET /api/sources    — list scrape sources with last-run info
  - GET /api/stats      — aggregate statistics
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.limiter import limiter
from app.models import Job, ScrapeLog, ScrapeStatus
from app.schemas import (
    JobListResponse,
    JobResponse,
    SourceInfo,
    SourcesResponse,
    StatsResponse,
)

router = APIRouter(prefix="/api", tags=["jobs"])


# ── GET /api/jobs ───────────────────────────────────────────────────────

@router.get("/jobs", response_model=JobListResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def list_jobs(
    request: Request,
    q: str | None = Query(None, description="Full-text search across title, company, location"),
    location: str | None = Query(None, description="Filter by location (partial match)"),
    source: str | None = Query(None, description="Filter by source name"),
    visa_only: bool = Query(False, description="Show only jobs with visa sponsorship"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """
    Search and filter job listings with pagination.

    Supports optional full-text search via the `q` parameter which
    matches against title, company, and location fields.
    """
    # Build base query
    query = select(Job).where(Job.is_active == True)

    # Full-text search across title, company, location
    if q:
        like_pattern = f"%{q}%"
        query = query.where(
            Job.title.ilike(like_pattern)
            | Job.company.ilike(like_pattern)
            | Job.location.ilike(like_pattern)
            | Job.description.ilike(like_pattern)
        )

    # Filters
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if source:
        query = query.where(Job.source == source)
    if visa_only:
        query = query.where(Job.visa_sponsorship == True)

    # Count total matching results
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Job.scraped_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


# ── GET /api/jobs/{id} ──────────────────────────────────────────────────

@router.get("/jobs/{job_id}", response_model=JobResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def get_job(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Retrieve a single job listing by its ID.

    Returns 404 if the job does not exist or has been deactivated.
    """
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.is_active == True)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


# ── GET /api/sources ────────────────────────────────────────────────────

@router.get("/sources", response_model=SourcesResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def list_sources(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SourcesResponse:
    """
    List all known scrape sources with their status.

    Returns the last scrape time, status, and total job count per source.
    Frontend uses this to display which sources are active.
    """
    # Get distinct sources from jobs table
    sources_result = await db.execute(
        select(Job.source, Job.tier).distinct()
    )
    source_rows = sources_result.all()

    sources_info = []
    for source_name, tier in source_rows:
        # Last scrape log for this source
        log_result = await db.execute(
            select(ScrapeLog)
            .where(ScrapeLog.source == source_name)
            .order_by(ScrapeLog.run_at.desc())
            .limit(1)
        )
        last_log = log_result.scalar_one_or_none()

        # Total active jobs count
        count_result = await db.execute(
            select(func.count())
            .where(Job.source == source_name, Job.is_active == True)
        )
        total_jobs = count_result.scalar_one()

        sources_info.append(
            SourceInfo(
                name=source_name,
                tier=tier.value if hasattr(tier, "value") else str(tier),
                last_scrape=last_log.run_at if last_log else None,
                last_status=last_log.status.value if last_log else None,
                total_jobs=total_jobs,
            )
        )

    return SourcesResponse(sources=sources_info)


# ── GET /api/stats ──────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def get_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StatsResponse:
    """
    Return aggregate statistics for dashboard display.

    Includes total jobs, jobs added today, number of active sources,
    and the timestamp of the most recent scrape.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total active jobs
    total_result = await db.execute(
        select(func.count()).where(Job.is_active == True)
    )
    total_jobs = total_result.scalar_one()

    # Jobs added today
    new_result = await db.execute(
        select(func.count())
        .where(Job.is_active == True, Job.created_at >= today_start)
    )
    new_today = new_result.scalar_one()

    # Distinct active sources
    sources_result = await db.execute(
        select(func.count(Job.source.distinct())).where(Job.is_active == True)
    )
    sources_online = sources_result.scalar_one()

    # Last scrape time
    last_result = await db.execute(
        select(ScrapeLog.run_at)
        .where(ScrapeLog.status == ScrapeStatus.SUCCESS)
        .order_by(ScrapeLog.run_at.desc())
        .limit(1)
    )
    last_scrape = last_result.scalar_one_or_none()

    return StatsResponse(
        total_jobs=total_jobs,
        new_today=new_today,
        sources_online=sources_online,
        last_scrape_at=last_scrape,
    )




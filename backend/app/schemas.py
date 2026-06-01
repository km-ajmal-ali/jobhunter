"""
Pydantic schemas for API request/response validation.

Separated from models.py to maintain a clean API contract
that doesn't leak ORM internals to the client.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, HttpUrl


# ── Job Schemas ─────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    """Schema returned by GET /api/jobs and GET /api/jobs/{id}."""
    id: int
    title: str
    company: str
    location: str | None
    source: str
    source_url: str
    company_url: str | None
    apply_url: str | None
    description: str | None
    salary_range: str | None
    tags: list[str] | None
    posted_at: datetime | None
    visa_sponsorship: bool
    tier: str
    scraped_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Paginated response wrapper for job listings."""
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Location Schemas ────────────────────────────────────────────────────

class LocationInfo(BaseModel):
    """A single job location entry."""
    name: str
    job_count: int


class LocationsResponse(BaseModel):
    """Response wrapper for /api/locations."""
    locations: list[LocationInfo]


# ── Source Schemas ──────────────────────────────────────────────────────

class SourceInfo(BaseModel):
    """Status information for a single scrape source."""
    name: str
    tier: str
    last_scrape: datetime | None
    last_status: str | None
    total_jobs: int


class SourcesResponse(BaseModel):
    """Response wrapper for the /api/sources endpoint."""
    sources: list[SourceInfo]


# ── Country Schemas ───────────────────────────────────────────────────

class CountryInfo(BaseModel):
    """A single country entry from job locations."""
    name: str
    code: str
    job_count: int


class CountriesResponse(BaseModel):
    """Response wrapper for /api/countries."""
    countries: list[CountryInfo]


# ── Stats Schemas ───────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    """Dashboard statistics returned by GET /api/stats."""
    total_jobs: int
    new_today: int
    sources_online: int
    last_scrape_at: datetime | None

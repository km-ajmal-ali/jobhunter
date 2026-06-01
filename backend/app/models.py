"""
SQLAlchemy ORM models for the JobHunter database.

Tables:
  - `jobs` — stores all scraped job listings
  - `scrape_logs` — records each scrape run for monitoring
  - `locations` — lookup table for job locations (populated after each scrape)
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScrapeTier(enum.Enum):
    """
    Identifies whether a scrape source is low-risk (permitted) or high-risk (ToS-restricted).
    - TIER1: Scraped daily — permitted sites
    - TIER2: Scraped weekly — risky sites
    """
    TIER1 = "TIER1"
    TIER2 = "TIER2"


class ScrapeStatus(enum.Enum):
    """Status of a single scrape run."""
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Location(Base):
    """
    Lookup table of distinct job locations.

    Populated after each scrape run from active jobs.
    """
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    """Location display name (e.g. 'San Francisco, CA')."""

    job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    """Number of active jobs in this location."""

    def __repr__(self) -> str:
        return f"<Location id={self.id} name='{self.name}'>"


class Country(Base):
    """
    Lookup table of countries derived from job locations.
    """
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    """Country display name (e.g. 'United States')."""

    code: Mapped[str] = mapped_column(String(4), nullable=False, unique=True)
    """ISO 3166-1 alpha-2 code (e.g. 'US')."""

    job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    """Number of active jobs in this country."""

    def __repr__(self) -> str:
        return f"<Country id={self.id} code='{self.code}' name='{self.name}'>"


class Job(Base):
    """
    Represents a single job listing scraped from any source.

    Deduplication is handled via the unique constraint on (source, source_url).
    """
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)

    company: Mapped[str] = mapped_column(String(256), nullable=False, index=True)

    location: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)

    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    company_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    apply_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    """Direct application URL (if different from source_url)."""

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    salary_range: Mapped[str | None] = mapped_column(String(128), nullable=True)

    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    """Tags for department, tech stack, or category (e.g. ['Engineering', 'Python', 'React'])."""

    country_code: Mapped[str | None] = mapped_column(String(4), nullable=True, index=True)
    """ISO 3166-1 alpha-2 country code derived from location string."""

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    visa_sponsorship: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    tier: Mapped[ScrapeTier] = mapped_column(
        Enum(ScrapeTier, name="scrape_tier"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("source", "source_url", name="uq_job_source_url"),
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title='{self.title}' company='{self.company}'>"


class ScrapeLog(Base):
    """
    Records every scrape run for monitoring and debugging.
    Useful for the `/api/sources` endpoint to show last scrape times.
    """
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    """Source identifier matching the Job.source field."""

    tier: Mapped[ScrapeTier] = mapped_column(
        Enum(ScrapeTier, name="scrape_tier"),
        nullable=False,
    )
    """Which tier this scrape belongs to."""

    status: Mapped[ScrapeStatus] = mapped_column(
        Enum(ScrapeStatus, name="scrape_status"),
        nullable=False,
        default=ScrapeStatus.RUNNING,
    )
    """Current status of the scrape run."""

    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    """Total jobs found during this run."""

    jobs_new: Mapped[int] = mapped_column(Integer, default=0)
    """New jobs inserted (not already in DB)."""

    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Error message if the scrape failed."""

    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    """When this scrape run started."""

    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    """How long the scrape took in seconds."""

    def __repr__(self) -> str:
        return f"<ScrapeLog id={self.id} source='{self.source}' status='{self.status}'>"

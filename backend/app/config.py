"""
JobHunter Backend Configuration.

All environment-based configuration for the backend service.
Uses pydantic-settings to load from .env or environment variables.

Secrets and environment-specific values are never hardcoded here.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Naming convention:
      - Uppercase = env var name
      - Lowercase = Python attribute
    """

    # ── App ──────────────────────────────────────────────────────────
    APP_NAME: str = "JobHunter API"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://jobuser:jobpass@db:5432/jobhunter"
    """
    PostgreSQL connection string (async).
    Format: postgresql+asyncpg://user:password@host:port/dbname
    Default points to the `db` service in Docker Compose.
    """

    # ── Scraping ─────────────────────────────────────────────────────
    SCRAPER_TIER1_SCHEDULE_HOUR: int = 2
    """Hour (0-23) at which Tier 1 (permitted) scrapers run daily."""

    SCRAPER_TIER2_ENABLED: bool = False
    """Disable Tier 2 scrapers by default (safe for local dev). Set True in production."""

    SCRAPER_TIER2_SCHEDULE_HOUR: int = 3
    """Hour (0-23) at which Tier 2 (risky) scrapers run on Sundays."""

    SCRAPER_DELAY_MIN: float = 2.0
    """Minimum delay (seconds) between consecutive requests for Tier 2."""

    SCRAPER_DELAY_MAX: float = 6.0
    """Maximum delay (seconds) between consecutive requests for Tier 2."""

    SCRAPER_TIMEOUT: int = 30
    """HTTP request timeout in seconds."""

    # ── Proxy (optional) ─────────────────────────────────────────────
    PROXY_LIST: str = ""
    """
    Comma-separated proxy URLs for Tier 2 scrapers.
    Example: "http://proxy1:8080,http://proxy2:8080"
    Leave empty to connect directly.
    """

    # ── CORS ──────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    """Comma-separated allowed CORS origins."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
"""
Singleton settings instance. Import this anywhere you need config.
Usage:
    from app.config import settings
    print(settings.DATABASE_URL)
"""

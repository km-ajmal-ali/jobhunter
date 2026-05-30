"""
Database setup using SQLAlchemy 2.0 async support.

Provides:
  - `engine` — the async SQLAlchemy engine
  - `AsyncSessionLocal` — factory for async database sessions
  - `Base` — declarative base for models
  - `get_db()` — FastAPI dependency yielding a session per request
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ── Engine ──────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# ── Session Factory ─────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base Model ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy ORM models.
    Every model should inherit from this.
    """
    pass


# ── Dependency ──────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Yields:
        An AsyncSession that is automatically closed when the request ends.

    Usage:
        @router.get("/jobs")
        async def list_jobs(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

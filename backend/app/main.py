"""
JobHunter Backend — FastAPI Application Entry Point.

Initialises the FastAPI app, configures CORS, registers routers,
and starts the APScheduler for periodic scraping jobs.

Run (development):
    uvicorn app.main:app --reload

Run (production):
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.jobs import router as jobs_router
from app.routers.scrape import router as scrape_router
from app.scrapers.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    - Startup: initialises the APScheduler to begin daily/weekly scraping.
    - Shutdown: gracefully stops the scheduler.
    """
    # ── Startup ────────────────────────────────────────────────────────
    start_scheduler()
    yield
    # ── Shutdown ───────────────────────────────────────────────────────
    stop_scheduler()


# ── App Initialisation ──────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────
# Allow the frontend (React dev server or Nginx-served build) to call the API.

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────

app.include_router(jobs_router)
app.include_router(scrape_router)


# ── Health Check ────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    Returns OK if the server is running.
    """
    return {"status": "ok", "service": settings.APP_NAME}

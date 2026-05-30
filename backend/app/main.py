"""
JobHunter Backend — FastAPI Application Entry Point.

Initialises the FastAPI app, configures CORS, rate limiting,
origin validation, registers routers, and starts the APScheduler.
"""
from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.limiter import limiter
from app.routers.jobs import router as jobs_router
from app.routers.scrape import router as scrape_router
from app.scrapers.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Origin / Referer validation ─────────────────────────────────────────
# Prevents direct curl/script access from unknown origins.

ALLOWED_ORIGIN_PATTERNS: list[re.Pattern] = []
if settings.ALLOWED_ORIGINS:
    for origin in settings.ALLOWED_ORIGINS.split(","):
        origin = origin.strip()
        if origin:
            ALLOWED_ORIGIN_PATTERNS.append(re.compile(re.escape(origin)))


def _origin_allowed(request: Request) -> bool:
    if not ALLOWED_ORIGIN_PATTERNS:
        return True  # No restriction configured
    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    for pattern in ALLOWED_ORIGIN_PATTERNS:
        if pattern.search(origin) or pattern.search(referer):
            return True
    return False


# ── Lifespan ────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
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

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting middleware ────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# ── Origin validation middleware ────────────────────────────────────────


@app.middleware("http")
async def validate_origin(request: Request, call_next):
    if not _origin_allowed(request):
        logger.warning("Blocked request from disallowed origin: %s", request.headers.get("origin", "unknown"))
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    return await call_next(request)


# ── Routers ─────────────────────────────────────────────────────────────

app.include_router(jobs_router)
app.include_router(scrape_router)


# ── Health Check ────────────────────────────────────────────────────────


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}

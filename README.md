# JobHunter

A job board at [visajobsforyou.com](https://www.visajobsforyou.com) for one specific, underserved audience: people who need visa sponsorship to work abroad. Regular job boards bury this signal — you apply to a hundred listings before realizing none of them sponsor. This site flips that: every listing on it is already known to be visa-friendly, because that's the only kind of listing it collects.

## The business, in plain terms

There's no sales team, no employer dashboard, no one paying to post a job. The site scrapes job listings from sources known to sponsor visas (or to specialize in relocation hiring), normalizes them into one searchable database, and shows them to job seekers for free. Revenue comes entirely from Google AdSense impressions on the site — so the model only works if the content stays fresh and people keep coming back to search. That's why scraping runs on autopilot every single day rather than being a manual, occasional chore.

It's a small, quiet, SEO-and-ads play: be the best free resource for "does this company sponsor visas," rank for that in search, and let ad impressions cover the (modest) hosting bill. There's a dynamic `sitemap.xml` and `robots.txt` specifically so search engines index every job page — that traffic is the whole growth strategy, there's no paid acquisition.

## How it's built

Two services behind Nginx, backed by one Postgres database:

- **Backend** (`backend/`) — FastAPI + SQLAlchemy (async) + APScheduler, all living in one Python process. It does three jobs: scrape sources on a schedule, store what it finds, and serve that data over a REST API.
- **Frontend** (`frontend/`) — a small React + TypeScript SPA (Vite, Tailwind) that searches, filters, and displays listings. Built to static files and served by Nginx in production.
- **Nginx** — serves the built frontend, reverse-proxies `/api/*` to the backend, and handles the `visajobsforyou.com` → `www.` redirect. TLS is terminated upstream by Cloudflare, so Nginx itself only speaks plain HTTP.

### The scraper, and why it's split into tiers

This is the part that actually matters for understanding the codebase. Scraping other people's websites lives in a legal and ethical gray zone that gets darker depending on the source — so sources are explicitly split by risk in `backend/app/scrapers/`:

- **Tier 1** (`scrapers/tier1/`) — sites that are fine to scrape: visa-sponsorship job boards, relocation sites, GitHub-curated company lists. Runs **daily**, automatically, no flag needed.
- **Tier 2** (`scrapers/tier2/`) — LinkedIn, Indeed, Glassdoor. These actively police scraping in their Terms of Service. The code exists, but it's **disabled by default** (`SCRAPER_TIER2_ENABLED=false`) and only meant to run weekly, deliberately slow (randomized delays, proxy support), if someone makes a conscious decision to turn it on. Nothing about this is automatic.

All scrapers share one base class (`scrapers/base.py`) that handles the boring, easy-to-get-wrong stuff once: HTTP client setup, user-agent rotation, retry/backoff, and de-duplicated upserts into the `jobs` table (uniqueness is enforced on `source` + `source_url`, so the same listing scraped twice never becomes two rows). Every run is logged to `scrape_logs`, which is what powers the "last scraped" status you can see via `/api/sources`.

APScheduler runs inside the same process as the web server (see the FastAPI `lifespan` in `backend/app/main.py`) — there's no separate worker or cron container. Simple, and fine at this scale.

### The API

A handful of read endpoints under `/api` — jobs (search/filter/paginate), a single job by ID, sources (scrape health), countries and locations (for filter dropdowns), and stats (counts for the homepage). There's also one write-ish endpoint, `POST /api/scrape/trigger`, for kicking off a scrape manually instead of waiting for the schedule — it's locked behind an API key (`SCRAPE_API_KEY`) so it can't be hit by randoms.

Two layers quietly protect the API from abuse: rate limiting per IP (`slowapi`), and an origin/referer check (`ALLOWED_ORIGINS`) that rejects requests not coming from the real site — so someone can't just `curl` the API from a script, but search crawlers and the site itself still get through.

### Deployment

Fully automated, start to finish, via `.github/workflows/deploy.yml`: a push to `release` builds both Docker images, pushes them to GHCR, SSHes into a single VPS, and runs `docker compose up -d` plus Alembic migrations. No staging environment, no manual approval step — this is a side project sized for one person to maintain, not a team.

The one non-obvious piece of operational care: `scripts/check-health.sh`. This project runs on a memory-constrained VPS (see the `mem_limit`s in `docker-compose.yml`), so containers occasionally get OOM-killed. The deploy workflow installs this script as a cron job (every 5 minutes) that checks container health and kernel OOM logs, and fires a webhook alert (Slack/Discord-style) if anything's down. It's the "find out before a user does" safety net for a site with no dedicated ops team.

## Running it locally

```bash
cp .env.example .env     # fill in DB credentials, etc.
docker compose up -d     # db + backend + frontend
docker compose exec backend alembic upgrade head
```

Backend API: `http://localhost:8000` (docs at `/docs`). Frontend dev server (hot reload, separate from the Docker build): `cd frontend && npm install && npm run dev`.

## Goal
- Build and run a Dockerized SaaS app (React frontend + FastAPI backend + PostgreSQL) that scrapes visa-sponsorship job listings and serves them on a public ad-supported website, deployable via GitHub Actions CI/CD (GHCR push → SSH deploy to EC2/VPS).

## Constraints & Preferences
- **Tech stack:** Frontend = React/Vite/Tailwind, Backend = Python FastAPI, Database = PostgreSQL, Container = Docker/Podman Compose, CI/CD = GitHub Actions (GHCR)
- **Auth:** No user authentication (public site)
- **Ads:** Google AdSense (publisher ID placeholder: `ca-pub-REPLACE_WITH_YOUR_ID`)
- **Scraping:** Two-tier schedule — Tier 1 (permitted sites) runs daily @ 2AM; Tier 2 (risky: LinkedIn, Indeed, Glassdoor) runs weekly Sundays @ 3AM with user-agent rotation + random delays (2–6s), gated by `SCRAPER_TIER2_ENABLED` (default `false`)
- **Deployment:** GitHub Actions → build images → push to GHCR → SSH deploy to EC2/VPS; local dev uses Podman Compose
- **Secrets never in repo:** `GHCR_TOKEN`, `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`, `SSH_PORT` stored as GitHub Secrets; `.env` auto-created on EC2 by deploy script
- **Domain:** Not yet purchased — SSL/domain setup deferred via script (`scripts/deploy-domain.sh`)

## Progress
### Done
- Full project scaffolded: 46+ files across backend, frontend, Docker, and DevOps
- Backend: FastAPI app, async SQLAlchemy models (`Job`, `ScrapeLog`), 4 API endpoints (`/api/jobs`, `/api/jobs/{id}`, `/api/sources`, `/api/stats`), Alembic raw-SQL migration (001)
- Scraper framework: `BaseScraper` with retry/UA rotation/upsert, `APScheduler` for scheduling, `deactivate_stale_jobs()` method added to `run()` pipeline; `ScrapeLog` integration
- Frontend: React 18 + Vite + Tailwind, `Home` page (search/filters/pagination/stats/AdSense slots), `JobDetail` page (full job info + "Visit Company Website" CTA), typed API client, `AdSlot` component
- Docker: `Dockerfile.frontend` (multi-stage node→nginx), `Dockerfile.backend` (python:3.12-slim), `docker-compose.yml` (3 services + nginx reverse proxy)
- DevOps: `.github/workflows/deploy.yml` (build → GHCR push → SCP config → SSH deploy), `scripts/setup-vps.sh`, `scripts/deploy-domain.sh`, `.env.example`
- `SCRAPER_TIER2_ENABLED` config flag (default `False`) — wraps Tier 2 jobs in scheduler
- Manual trigger endpoint `POST /api/scrape/trigger` in `routers/scrape.py` — calls `run_scrapers_tier1()`
- Podman Compose stack running locally: all 3 containers healthy
- **RelocateMeScraper** (`tier1/relocate.py`) built and tested — scrapes 10 job categories on `/international-jobs`, finds **20 real jobs**
- **GlobalSponsorHubScraper** (`tier1/globalsponsorhub.py`) built — discovers jobs via sitemap, found **1 job**
- **GitHubCompaniesScraper** (`tier1/github_companies.py`) built — uses Greenhouse JSON API for 10 companies, ~**1,950 jobs**
- Source labels changed from generic `"github-companies"` to per-company slugs; `save_jobs()` overridden for per-company source in job records
- **Stale job cleanup** added to `BaseScraper.run()` — marks jobs `is_active=False` when `source_url` no longer in current batch
- **Data quality bugs fixed:** HTML fallback removed from GitHubCompaniesScraper; visasponsor company parser strips "View all jobs" suffix
- DB has **2,000 active jobs** across 14 source labels
- **GitHub repo created:** `km-ajmal-ali/jobhunter` (public), pushed with `main` branch
- **CI/CD pipeline fixed iteratively:**
  - Removed `cache-from`/`cache-to` from `build-push-action` (default docker driver doesn't support it)
  - Replaced heredoc `<< 'EOF'` with `echo` statements (YAML `<<` merge key syntax conflict)
  - Added `appleboy/scp-action@v0.1.7` step to copy `docker-compose.yml` to EC2
  - Added auto-creation of `.env` on EC2 with defaults and random `DB_PASSWORD`
  - Removed `nginx/nginx.conf` SCP source and volume mount (config is baked into Docker image)
- Fixed nginx healthcheck failure: removed `:ro` volume mount for `nginx.conf` — entrypoint script `10-listen-on-ipv6-by-default.sh` couldn't modify a read-only mount; now uses the config baked into the image at build time

### In Progress
- **EC2 deployment:** All 3 containers running but frontend is **unhealthy** (post-fix, awaiting pipeline re-run)
- **EC2 security group:** Only SSH inbound rule added — HTTP (port 80) needs to be opened to `0.0.0.0/0`

### Blocked
- H1BGrader scraper blocked by Cloudflare (403) — even `cloudscraper` cannot bypass
- H1Base scraper gets connection refused (site appears down)
- Tier 2 scrapers (LinkedIn, Indeed, Glassdoor) not tested — require `SCRAPER_TIER2_ENABLED=true`
- 17 companies from GitHub list remain unscrapable: use custom career sites without JSON-LD JobPosting schemas or standard ATS APIs
- Myvisajobs.com: all pages redirect to 404 (site appears broken)
- globalsponsorhub.com: listing pages JS-rendered, only 1 job in sitemap, not practically scrapable
- Mobile LAN access on Windows: Podman binds published ports to `127.0.0.1` only — requires firewall + `netsh portproxy` or VPN

## Key Decisions
- **Removed Playwright** from dependencies — scrapers use `httpx` + `BeautifulSoup` with user-agent rotation + delays instead
- **Raw SQL migration** instead of `op.create_table` — avoids SQLAlchemy ORM enum creation conflicts with PostgreSQL native enums
- **Uppercase enum labels** in PostgreSQL (`TIER1`, `TIER2`, `RUNNING`, `SUCCESS`, `FAILED`)
- **Removed `str` mixin** from enum classes — SQLAlchemy now uses `.value` correctly
- **podman-compose** used instead of docker-compose on Windows (Podman 5.8.2 + podman-compose 1.5.0 via pip)
- **`SCRAPER_TIER2_ENABLED=False` by default** — Tier 2 scrapers are risky and should only run in production
- **Seed data removed** — only real scraped jobs are kept
- **Stale job cleanup in `run()` pipeline:** `deactivate_stale_jobs()` marks jobs `is_active=False` when `source_url` not in fresh batch; handles `list[dict]` and `dict[str, list[dict]]` return types via `isinstance()`
- **No nginx volume mount in production** — `nginx.conf` is baked into the Docker image at build time; the `:ro` mount broke the nginx entrypoint and caused the container to be unhealthy
- **`.env` auto-created on EC2** by deploy script — no secrets in the public repo
- **`GHCR_TOKEN` must be a PAT with `write:packages` scope** — not an EC2 `.pem` key (common mistake)
- **EC2 security group must allow SSH + HTTP from `0.0.0.0/0`** for GitHub Actions to connect and for public web access

## Next Steps
1. Add HTTP (port 80) inbound rule to EC2 security group — then access `http://<EC2-PUBLIC-IP>` in browser
2. Re-run the CI/CD pipeline to apply the nginx volume mount fix and get the frontend healthy
3. Replace `ca-pub-REPLACE_WITH_YOUR_ID` in `index.html` and `AdSlot.tsx` with real AdSense IDs before production
4. Buy domain, point DNS, run `scripts/deploy-domain.sh` for SSL
5. For mobile LAN access: recommend Tailscale/ZeroTier VPN or SSH tunnel
6. Consider adding `is_active` filter to `/api/jobs` endpoint for debugging

## Critical Context
- **Podman PATH issue:** `podman-compose.exe` at `C:\Users\entiz\AppData\Roaming\Python\Python314\Scripts\` — must be called with full path or added to PATH
- **Frontend builds:** TypeScript strict mode — `import.meta.env` requires `vite-env.d.ts`; `??` and `||` operators cannot be mixed without parentheses
- **Podman port binding on Windows:** Published ports always bind to `127.0.0.1` — LAN access requires firewall + `netsh portproxy` or a VPN
- **Current DB:** 2,000 active jobs across 14 source labels
- **`docker-compose.yml`** removed `./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro` volume mount — config is baked into image; the `:ro` mount caused nginx entrypoint failure and unhealthy container
- **EC2 containers running** but frontend unhealthy (post-fix, awaiting re-deploy)
- **CI/CD build cache removed** — `cache-from: type=gha` / `cache-to: type=gha,mode=max` not supported on default docker driver; removed from both build steps
- **GitHub Secrets required:** `GHCR_TOKEN` (PAT with `write:packages`), `SSH_PRIVATE_KEY` (EC2 .pem content), `SSH_HOST`, `SSH_USER`, `SSH_PORT`
- **EC2 security group must allow** inbound SSH (port 22) + HTTP (port 80) from `0.0.0.0/0`

## Relevant Files
- `backend/app/main.py`: FastAPI entry point + lifespan (start/stop APScheduler)
- `backend/app/config.py`: `SCRAPER_TIER2_ENABLED` config field
- `backend/app/scrapers/base.py`: `BaseScraper` — abstract `fetch`/`parse`, `save_jobs` upsert, `deactivate_stale_jobs` with `isinstance()` for list vs dict returns
- `backend/app/scrapers/scheduler.py`: APScheduler — 6 Tier 1 scrapers registered; `run_scrapers_tier1()` manual trigger; Tier 2 gated by `SCRAPER_TIER2_ENABLED`
- `backend/app/scrapers/tier1/relocate.py`: `RelocateMeScraper` — 10 categories, 20 jobs
- `backend/app/scrapers/tier1/globalsponsorhub.py`: `GlobalSponsorHubScraper` — sitemap-based, 1 job
- `backend/app/scrapers/tier1/github_companies.py`: `GitHubCompaniesScraper` — Greenhouse API, 10 companies, per-company source labels, ~1,950 jobs
- `backend/app/scrapers/tier1/visasponsor.py`: `VisaSponsorJobsScraper` — 3 pages, 30 jobs
- `backend/app/scrapers/tier1/h1bgrader.py`: Cloudflare-blocked (403)
- `backend/app/scrapers/tier1/h1base.py`: Site down (connection refused)
- `backend/app/scrapers/tier2/`: LinkedIn + Indeed + Glassdoor scrapers (not tested)
- `backend/app/routers/jobs.py`: 4 API endpoints — `/api/jobs` supports `?source=`, `?q=`, `?location=`, `?visa_only=`
- `backend/app/routers/scrape.py`: `POST /api/scrape/trigger` — manual Tier 1 trigger
- `frontend/src/pages/Home.tsx`: Main search page with ad slots, job card grid (uniform width, truncation, hover tooltips)
- `frontend/src/pages/JobDetail.tsx`: Job detail page with "Visit Company Website" button
- `frontend/src/components/JobCard.tsx`: Job card with `flex h-full w-full min-w-0 flex-col`, truncation + `title` attribute, `mt-auto` pinned bottom section
- `frontend/src/components/AdSlot.tsx`: AdSense unit component
- `docker-compose.yml`: 3-service stack, frontend port `0.0.0.0:80:80`, nginx volume mount removed (config baked into image)
- `.github/workflows/deploy.yml`: CI/CD pipeline — build → GHCR push → SCP `docker-compose.yml` → SSH deploy with auto `.env` creation, alembic migrations
- `scripts/setup-vps.sh`: One-time VPS setup script
- `scripts/deploy-domain.sh`: Domain + SSL setup via Certbot
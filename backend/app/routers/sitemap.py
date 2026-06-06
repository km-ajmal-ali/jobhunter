from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job

router = APIRouter(tags=["sitemap"])

SITEMAP_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'
SITEMAP_ROOT_OPEN = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
SITEMAP_ROOT_CLOSE = "</urlset>"
BASE_URL = "https://www.visajobsforyou.com"


def _url_tag(loc: str, lastmod: str | None = None, changefreq: str = "weekly", priority: str = "0.5") -> str:
    parts = [f"  <loc>{loc}</loc>"]
    if lastmod:
        parts.append(f"  <lastmod>{lastmod}</lastmod>")
    parts.append(f"  <changefreq>{changefreq}</changefreq>")
    parts.append(f"  <priority>{priority}</priority>")
    return "<url>\n" + "\n".join(parts) + "\n</url>"


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap(db: AsyncSession = Depends(get_db)):
    urls = []

    urls.append(_url_tag(f"{BASE_URL}/", changefreq="daily", priority="1.0"))

    result = await db.execute(
        select(Job.id, Job.posted_at, Job.scraped_at).where(Job.is_active == True)
    )
    rows = result.all()

    for job_id, posted_at, scraped_at in rows:
        lastmod = (posted_at or scraped_at).strftime("%Y-%m-%d") if (posted_at or scraped_at) else None
        urls.append(
            _url_tag(
                f"{BASE_URL}/jobs/{job_id}",
                lastmod=lastmod,
                changefreq="weekly",
                priority="0.8",
            )
        )

    content = f"{SITEMAP_HEADER}\n{SITEMAP_ROOT_OPEN}\n" + "\n".join(urls) + f"\n{SITEMAP_ROOT_CLOSE}\n"
    from fastapi.responses import Response
    return Response(content=content, media_type="application/xml")

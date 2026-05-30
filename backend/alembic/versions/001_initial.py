"""
Initial migration: creates `jobs` and `scrape_logs` tables.

Revision ID: 001
Revises: None
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types (idempotent) ───────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE scrape_tier AS ENUM ('TIER1', 'TIER2');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE scrape_status AS ENUM ('RUNNING', 'SUCCESS', 'FAILED');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ── jobs table ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id              SERIAL PRIMARY KEY,
            title           VARCHAR(512) NOT NULL,
            company         VARCHAR(256) NOT NULL,
            location        VARCHAR(256),
            source          VARCHAR(64) NOT NULL,
            source_url      VARCHAR(2048) NOT NULL,
            company_url     VARCHAR(2048),
            description     TEXT,
            salary_range    VARCHAR(128),
            posted_at       TIMESTAMPTZ,
            visa_sponsorship BOOLEAN NOT NULL DEFAULT FALSE,
            tier            scrape_tier NOT NULL,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (source, source_url)
        )
    """)

    # Indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_title ON jobs (title)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_company ON jobs (company)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_location ON jobs (location)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_source ON jobs (source)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_visa_sponsorship ON jobs (visa_sponsorship)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_is_active ON jobs (is_active)")

    # ── scrape_logs table ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS scrape_logs (
            id              SERIAL PRIMARY KEY,
            source          VARCHAR(64) NOT NULL,
            tier            scrape_tier NOT NULL,
            status          scrape_status NOT NULL DEFAULT 'RUNNING',
            jobs_found      INTEGER NOT NULL DEFAULT 0,
            jobs_new        INTEGER NOT NULL DEFAULT 0,
            error_msg       TEXT,
            run_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            duration_seconds FLOAT
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_scrape_logs_source ON scrape_logs (source)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS jobs CASCADE")
    op.execute("DROP TABLE IF EXISTS scrape_logs CASCADE")
    op.execute("DROP TYPE IF EXISTS scrape_tier")
    op.execute("DROP TYPE IF EXISTS scrape_status")

"""
Migration 003: create countries table; add country_code to jobs.

Revision ID: 003
Revises: 002
Create Date: 2026-06-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(128) NOT NULL UNIQUE,
            code        VARCHAR(4) NOT NULL UNIQUE,
            job_count   INTEGER NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_countries_code ON countries (code)")
    op.execute("""
        ALTER TABLE jobs
        ADD COLUMN IF NOT EXISTS country_code VARCHAR(4)
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_country_code ON jobs (country_code)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS countries CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_jobs_country_code")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS country_code")

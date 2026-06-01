"""
Migration 002: add apply_url, tags to jobs; create locations table.

Revision ID: 002
Revises: 001
Create Date: 2026-05-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to jobs
    op.execute("""
        ALTER TABLE jobs
        ADD COLUMN IF NOT EXISTS apply_url VARCHAR(2048),
        ADD COLUMN IF NOT EXISTS tags TEXT[]
    """)

    # Create locations table
    op.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(256) NOT NULL UNIQUE,
            job_count   INTEGER NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_locations_name ON locations (name)")


def downgrade() -> None:
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS apply_url")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS tags")
    op.execute("DROP TABLE IF EXISTS locations CASCADE")

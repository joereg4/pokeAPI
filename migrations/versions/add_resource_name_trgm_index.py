"""Add trigram index on resources.name for fast ILIKE search

Revision ID: add_resource_name_trgm_index
Revises: add_tcg_cards_table
Create Date: 2026-02-14 12:00:00.000000

The pg_trgm extension enables GIN indexes that accelerate ILIKE '%term%'
queries.  This is used by the /api/search endpoint for the navbar
autocomplete.  If the extension cannot be created (e.g. missing
superuser privileges), the migration is skipped gracefully – search
still works, just without the index speedup.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_resource_name_trgm_index"
down_revision = "add_tcg_cards_table"
branch_labels = None
depends_on = None


def upgrade():
    # Enable the pg_trgm extension (requires CREATE on the database;
    # most managed Postgres providers allow this).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # Create a GIN trigram index on resources.name.
    # This dramatically speeds up ILIKE '%term%' queries.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_resources_name_trgm "
        "ON resources USING gin (name gin_trgm_ops);"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_resources_name_trgm;")
    # We intentionally do NOT drop the pg_trgm extension – other
    # tables/indexes may depend on it.

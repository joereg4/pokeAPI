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

import logging
from alembic import op
from sqlalchemy import text

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = "add_resource_name_trgm_index"
down_revision = "add_tcg_cards_table"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Step 1: Try to enable pg_trgm. This requires CREATE privilege on the
    # database, which the app user may not have. If it fails we log a
    # warning and skip the GIN index (search still works, just slower).
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        logger.info("pg_trgm extension is available.")
    except Exception as e:
        logger.warning(
            "Could not create pg_trgm extension (%s). "
            "Skipping trigram index – search will still work, "
            "just without the index speedup. "
            "Ask a superuser to run: CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            e,
        )
        return  # Can't create the index without the extension

    # Step 2: Create the GIN trigram index on resources.name.
    # This dramatically speeds up ILIKE '%term%' queries.
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_resources_name_trgm "
            "ON resources USING gin (name gin_trgm_ops);"
        )
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_resources_name_trgm;")
    # We intentionally do NOT drop the pg_trgm extension – other
    # tables/indexes may depend on it.

#!/bin/bash
# Optional init hook for postgres first start.
# Default clone-and-run uses seed.sql (empty) + flask db upgrade in the app container.

set -e

if [ -f /docker-entrypoint-initdb.d/seed.sql ]; then
    echo "Running seed.sql bootstrap..."
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/seed.sql
    echo "Seed complete."
fi

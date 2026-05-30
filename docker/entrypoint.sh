#!/bin/bash
set -e
flask db upgrade
python scripts/seed_resources_if_empty.py
exec "$@"

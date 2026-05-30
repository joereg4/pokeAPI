-- Docker PostgreSQL bootstrap (sanitized — no production data).
--
-- Schema is created by Flask migrations, not this file. After first start:
--   docker compose run --rm app flask db upgrade
--   docker compose run --rm app python manage.py create_user
--
-- For a production dump, use a local operator-only backup.sql (gitignored).

SELECT 1;

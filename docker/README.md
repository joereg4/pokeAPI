# Docker setup

Run the Pokédex locally with Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Copy environment template: `cp .env.example .env` and set `SECRET_KEY`

## Quick start

```bash
docker compose up --build
```

Open **http://localhost:8080** (or the port from `NGINX_PORT` in `.env`).

On first run (empty database), the app entrypoint automatically:

1. Runs `flask db upgrade`
2. Imports summaries from `static/resources/*.csv` via `scripts/seed_resources_if_empty.py`

Create an admin user for login and summary editing:

```bash
docker compose run --rm app python manage.py create_user
```

To re-import CSVs manually (skips rows that already exist):

```bash
docker compose run --rm app python scripts/migrate_pokemon_data.py
```

## Services

| Service | Role |
|---------|------|
| `app` | Gunicorn (Flask) on port 8000 |
| `nginx` | Reverse proxy (host port → container 80) |
| `db` | PostgreSQL 14 |
| `redis` | Redis 7 |

## Ports

- **8080** — default nginx URL (`NGINX_PORT=8080` in `.env.example`)
- **8000** — direct app access (optional smoke tests)

If port 80 is already in use on your machine, keep `NGINX_PORT=8080` (default).

## Database

- **Summaries:** `static/resources/*.csv` (committed) → imported on first app start when `resources` is empty
- **Users:** created manually with `python manage.py create_user` (not in CSV)
- **Optional TCG cards:** `python manage.py import_tcg_data`
- Committed SQL seed: `docker/db/seed.sql` (schema bootstrap only; no production data)
- Reset database: `docker compose down -v` (next start re-imports CSVs)

## Operator backup restore (local only)

To init Postgres from your own dump (never commit it):

1. Place `docker/db/backup.sql` locally (gitignored)
2. Temporarily mount it in `docker-compose.yml` under `db.volumes` instead of `seed.sql`
3. `docker compose down -v && docker compose up -d db`

## Troubleshooting

```bash
docker compose ps
docker compose logs app
docker compose logs nginx
```

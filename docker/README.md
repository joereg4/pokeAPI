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

On first run, apply migrations and create an admin user:

```bash
docker compose run --rm app flask db upgrade
docker compose run --rm app python manage.py create_user
```

The entrypoint runs `flask db upgrade` automatically on container start; you still need `create_user` for admin access.

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

- Committed seed: `docker/db/seed.sql` (empty bootstrap only)
- **No** production `backup.sql` in the repo — operator dumps stay local and gitignored
- Reset database: `docker compose down -v`

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

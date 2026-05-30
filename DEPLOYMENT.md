# Deployment Guide

This document covers **self-hosted** deployment patterns. For a quick local site, use Docker (see [README.md](README.md)).

## Local development (recommended)

1. `cp .env.example .env` and set `SECRET_KEY`
2. `docker compose up --build` OR `.venv` + Postgres + Redis ([README.md](README.md))
3. Open http://localhost:8080 (Docker) or http://127.0.0.1:5000 (Flask dev)

## Docker Compose (production-like local)

- Services: app, nginx, postgres, redis
- DB seed: migrations + CSV import on empty `resources` table (see [docker/README.md](docker/README.md))
- Env: `.env` (not committed)
- See [docker/README.md](docker/README.md) for ports and troubleshooting

First-time setup after `docker compose up`:

```bash
docker compose run --rm app python manage.py create_user
```

The entrypoint runs `flask db upgrade` and seeds summaries from `static/resources/*.csv` when the `resources` table is empty. Users are never seeded automatically — use `create_user` above.

For a non-Docker install, after `flask db upgrade` run:

```bash
python scripts/seed_resources_if_empty.py
python manage.py create_user
```

## Bare-metal outline (bring your own server)

1. Provision: Python 3.9+, PostgreSQL, Redis, nginx
2. Clone repo; create venv; `pip install -r requirements.txt`
3. Set all variables from `.env.example`
4. `flask db upgrade`
5. `python scripts/seed_resources_if_empty.py` (summaries from `static/resources/*.csv`)
6. Run gunicorn behind nginx (example unit files not included — adapt to your OS)

## What not to commit

- `.env`, `*.sql` dumps, `config/ga4-service-account.json`
- Production hostnames, SSH keys, API keys, or other secrets

## Database migrations

```bash
source .venv/bin/activate
flask db upgrade
```

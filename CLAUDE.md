# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run tests (default: parallel, no integration):**
```bash
pytest tests/
```

**Run a single test file:**
```bash
pytest tests/routes/test_pokemon.py -n 0
```

**Run a single test:**
```bash
pytest tests/routes/test_pokemon.py::test_pokemon_detail -n 0
```

**Run integration tests (hit real external APIs):**
```bash
pytest tests/ -m integration
```

**Start the development server:**
```bash
python app.py
```

**Database migrations:**
```bash
flask db migrate -m "description"
flask db upgrade
```

**Manage users via CLI:**
```bash
python manage.py create_user
python manage.py update_user
```

## Architecture

### Application Factory
`app.py` exports `create_app(test_config=None)`. It initializes Flask extensions in order: rate limiter → compression → cache (Redis) → pokedex shelve cache → SQLAlchemy → Flask-Login → blueprints.

### Blueprint Auto-Registration
`routes/__init__.py` dynamically imports every `.py` file in `routes/` and registers any `Blueprint` object found. Adding a new route file with a `Blueprint` variable is sufficient — no manual registration needed.

### Two-Level Caching
- **High-level**: Flask-Caching backed by Redis (`cache/` module). Used for route-level response caching with `@cache.cached()`. TTL defaults to 3600s.
- **Low-level**: Python `shelve` (filesystem). Used inside the `pokedex` module for raw API data. Initialized via `pokedex.cache.initialize_cache()`.

### Data Flow
Routes call `pokedex.APIResource.fetch_data(endpoint, id_or_name)` → checks shelve cache → fetches from PokéAPI via `pokedex.api` HTTP client → stores in shelve. Route responses are separately cached in Redis.

### Database Models (`models/model.py`)
- `User` — auth, admin flag, password hashing via Werkzeug
- `Resource` — cached AI-generated summaries (name, resource_type, summary)
- `TCGCard` — Pokémon TCG card data

### Summary Generation (`routes/summary_generators/`)
Uses OpenAI API to generate descriptive summaries for Pokémon, abilities, moves, items, etc. Summaries are stored in the `Resource` table and served from DB on subsequent requests.

### Key Environment Variables
- `FLASK_ENV` — `development`, `production`, or `testing`
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string (e.g. `redis://localhost:6379/0`)
- `SECRET_KEY` — Flask session key
- `GOOGLE_ANALYTICS_MEASUREMENT_ID` / `GOOGLE_ANALYTICS_PROPERTY_ID`
- `GOOGLE_APPLICATION_CREDENTIALS` — path to GA4 service account JSON
- `OPENAI_API_KEY` — for summary generation

## Testing

Tests use SQLite in-memory (never PostgreSQL) and `SimpleCache` (never Redis). Two autouse fixtures in `conftest.py` mock Redis and cache stats for every test.

**Key fixtures (`tests/conftest.py`):**
- `app` — test Flask app with SQLite + SimpleCache
- `client` — unauthenticated test client
- `auth_client` — client authenticated as admin
- `regular_auth_client` — client authenticated as non-admin
- `mock_api` — mock for `pokedex.APIResource.fetch_data`; use `mock_api.register(endpoint, id_or_name, data)` to set up responses
- `mock_requests` — mock for `requests.get`

Mock JSON data for tests lives in `mock_data/`.

## Development Workflow

This is the required workflow for all changes. Follow every step in order.

### 1. Update local main and create a feature branch
Always start from an up-to-date local main. Never commit directly to `main`.
```bash
git checkout main && git pull origin main
git checkout -b your-feature-name
```

### 2. Run tests in the venv before committing
```bash
source .venv/bin/activate
pytest tests/
```
All tests must pass before proceeding. Fix any failures first.

### 3. Commit and push
```bash
git add <files>
git commit -m "type: short description"
git push -u origin your-feature-name
```

### 4. Open a Pull Request and watch CI
```bash
gh pr create --title "..." --body "..."
gh run watch <run-id> --exit-status
```
Wait for CI to go green. Fix failures before merging — never merge a failing PR.

### 5. Merge into main and watch CI again
```bash
gh pr merge <pr-number> --merge --delete-branch
gh run watch <run-id> --exit-status
```
Get the new run ID with `gh run list --branch main --limit 3`. CI must pass on `main` before deploying.

### 6. Deploy (operator — private notes)

See [DEPLOYMENT.md](DEPLOYMENT.md) for self-hosted deployment. Never commit server IPs, SSH keys, or secrets.

The CI webhook step on `main` triggers production deploy when configured; see `CONTRIBUTING.md` for required GitHub secrets.

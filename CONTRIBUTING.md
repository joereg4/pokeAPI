# Contributing

Thanks for your interest in contributing to pokeAPI.

## Development setup

1. Fork and clone the repository
2. `cp .env.example .env` — set at least `SECRET_KEY`
3. **Docker (recommended):** `docker compose up --build` — see [docker/README.md](docker/README.md)
4. **Local Python:** `.venv`, Postgres, Redis — see [README.md](README.md)

## Tests

```bash
.venv/bin/pytest tests/ -q -m "not integration"
```

Run the full suite before opening a PR. CI uses the same marker on Ubuntu with Redis.

## Rebuilding CSS

Stylesheets are compiled from SCSS — do not edit files in `static/css` directly.
After changing anything in `scss/`:

```bash
npm install        # first time only
npm run sass:build
```

This compiles `scss/` to `static/css` via [Dart Sass](https://sass-lang.com/dart-sass/).

## Pull requests

- Branch from an up-to-date `main`
- Keep changes focused; include tests when behavior changes
- Ensure CI passes

## CI secrets (maintainers only)

| Secret | Purpose |
|--------|---------|
| `OPENAI_API_KEY` | Optional; used by tests that touch summary generation |

Forks and contributors do not need repository secrets for CI.

## Code of conduct

Be respectful in issues and reviews. Security issues: see [SECURITY.md](SECURITY.md).

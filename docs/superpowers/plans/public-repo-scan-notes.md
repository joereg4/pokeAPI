# Pre-public security scan (2026-05-30)

## gitleaks

Install (macOS):

```bash
brew install gitleaks
```

Run against this repo (full history):

```bash
cd /path/to/pokeAPI
gitleaks detect --source . --verbose
```

Optional: save a report:

```bash
gitleaks detect --source . --report-path /tmp/gitleaks-pokeapi.json --report-format json
```

Without installing locally (Docker):

```bash
docker run --rm -v "$(pwd):/repo" zricethezav/gitleaks:latest detect --source /repo --verbose
```

If secrets appear in **git history**, rotate those keys and consider `git filter-repo` or BFG before making the repo public.

- **Status:** Clean as of history purge (2026-05-30). `newrelic.ini` removed from all commits via `git filter-repo`.

## Current tree grep (high-risk patterns)

| Path | Finding | Severity | Fix task |
|------|---------|----------|----------|
| `README.md`, `CLAUDE.md`, `docs/database_management.md` | Production IP `149.28.243.132` in SSH examples | Medium (infra leakage) | Task 3 |
| `scripts/backup_db.py`, `scripts/upload_pokemon_summaries.py` | Hardcoded SSH host | Medium | Task 3 |
| `scripts/download_pokemon_summaries.py` | IP in docstrings/examples | Low | Task 3 |
| `docs/superpowers/plans/2026-05-30-public-repo-prep.md` | IP in plan audit table (documentation of issue) | Info | N/A |
| `.github/workflows/ci.yml` | Hardcoded deploy webhook URL `https://pokedexapi.com/webhook/` | Medium | Task 8 |

No live API keys, PEM private keys, or committed `.env` values found in the current working tree.

## Gitignored assets (expected, not scanned in tree)

- `.env`, `*.sql`, `config/ga4-service-account.json`

## History

History scan deferred until gitleaks is available. Recommend full history scan before making the repository public.

# Pre-public security scan (2026-05-30)

## gitleaks

- **Status:** Not installed on this machine (`gitleaks` not found in PATH).
- **Action before going public:** Install gitleaks and run `gitleaks detect --source . --verbose`. If secrets appear in git history, rotate keys and consider `git filter-repo` / BFG (requires user approval).

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

- `.env`, `DEPLOYMENT.md`, `*.sql`, `config/ga4-service-account.json`

## History

History scan deferred until gitleaks is available. Recommend full history scan before making the repository public.

# Public Repository Preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `pokeAPI` safe and welcoming as a public GitHub repo: no committed secrets or production infrastructure details, clear local/Docker onboarding, and operator-only deployment docs kept private.

**Architecture:** Split **public** docs (clone → `.env` → Docker or `.venv` → run) from **private** operator notes (real IPs, SSH, production deploy). Scrub hardcoded production values from tracked code; drive deploy scripts and webhooks via environment variables. Provide a **sanitized** Docker database seed so newcomers never need your production dump.

**Tech Stack:** Flask 3, PostgreSQL, Redis, Docker Compose, pytest, GitHub Actions

---

## Current state (audit summary)

| Area | Status |
|------|--------|
| `.env`, `DEPLOYMENT.md`, `*.sql`, GA4 JSON | Gitignored ✅ |
| Production IP `149.28.243.132` | In `README.md`, `CLAUDE.md`, `docs/database_management.md`, `scripts/*.py` ❌ |
| `docker-compose.yml` | Requires local `.env` + `docker/db/backup.sql` (real data risk) |
| `DEPLOYMENT.md` | Gitignored — good for private ops; **public** `DEPLOYMENT.md` needed for contributors |
| `.env.example` | Missing ❌ |
| README | Stale UI changelog at top; says `venv` not `.venv`; weak Docker path |
| Docker smoke | App/DB/Redis OK; nginx port 80 conflict on some hosts |
| History scan | Not done — run before going public |

---

## File map (what changes where)

| File | Role after work |
|------|-----------------|
| `.env.example` | Committed template — all required vars, no values |
| `DEPLOYMENT.md` | **Public** — local Docker, optional bare-metal outline, placeholders only |
| `DEPLOYMENT.private.md` or keep gitignored `DEPLOYMENT.md` | Your real IP/SSH/cron (never commit) |
| `README.md` | Primary onboarding: Docker (recommended) + `.venv` dev |
| `docs/docker.md` | Optional deep-dive for Compose troubleshooting |
| `docker/db/seed.sql` | Committed minimal schema + optional demo data (no real users) |
| `docker/db/backup.sql` | Remain gitignored; document as operator-only |
| `docker-compose.yml` | Default `8080:80`, `FLASK_ENV=development` for local, seed not backup |
| `scripts/backup_db.py`, `upload_*.py`, `download_*.py` | `PROD_SSH_HOST`, `PROD_APP_DIR` from env — no IPs in repo |
| `routes/webhook.py` | `DEPLOY_APP_DIR` env instead of `/var/www/pokeAPI` |
| `CLAUDE.md` | Remove production SSH one-liners; point to `.env.example` |
| `.github/workflows/ci.yml` | Webhook URL from secret only (already); document in CONTRIBUTING |
| `SECURITY.md` | How to report issues; no production contact leakage |

---

### Task 1: Baseline security scan (do first)

**Files:**
- Create: `docs/superpowers/plans/public-repo-scan-notes.md` (optional scratch; delete before merge if desired)
- No production code changes yet

- [ ] **Step 1: Install and run history scanner**

```bash
# macOS
brew install gitleaks
cd /Users/joereg4/pokeAPI
gitleaks detect --source . --verbose 2>&1 | tee /tmp/gitleaks-pokeapi.txt
```

Expected: Review output for `.env`, API keys, PEM blocks, private keys in **any** commit.

- [ ] **Step 2: Grep current tree for high-risk patterns**

```bash
cd /Users/joereg4/pokeAPI
rg -n "149\.28\.243\.132|sk-[a-zA-Z0-9]{20,}|BEGIN (RSA |OPENSSH )?PRIVATE|WEBHOOK_SECRET\s*=\s*['\"][^'\"]+['\"]|OPENAI_API_KEY\s*=\s*['\"]" \
  --glob '!{.venv,node_modules}/**' --glob '!.git/**'
```

Expected: Only placeholders or docs you're about to fix — not live secrets.

- [ ] **Step 3: Record findings**

List each hit: path, severity, fix task number. If gitleaks finds secrets in **history**, plan key rotation + `git filter-repo` / BFG before making public (separate sub-task with user approval).

- [ ] **Step 4: Commit notes (optional)**

```bash
git add docs/superpowers/plans/public-repo-scan-notes.md
git commit -m "docs: record pre-public security scan results"
```

---

### Task 2: Add `.env.example`

**Files:**
- Create: `.env.example`
- Modify: `README.md` (reference it in Setup)
- Modify: `.gitignore` (already has `!.env.example` — verify)

- [ ] **Step 1: Create `.env.example` with documented variables**

Use this committed template (adjust if grep finds more vars):

```bash
# Flask
FLASK_ENV=development
FLASK_APP=app.py
FLASK_DEBUG=1
SECRET_KEY=change-me-to-a-long-random-string

# Database (local dev — match docker-compose or your Postgres)
DATABASE_URL=postgresql://pokeapi:pokeapi@localhost:5432/pokeapi

# Redis
REDIS_URL=redis://localhost:6379/0

# PokéAPI / app tuning (optional — defaults exist)
BASE_URL=https://pokeapi.co/api/v2
CACHE_TIMEOUT=3600
POKEMON_PER_PAGE=60
ITEMS_PER_PAGE=50

# OpenAI (optional — only for AI summary features)
OPENAI_API_KEY=

# Pokémon TCG API (optional)
POKEMONTCG_IO_API_KEY=

# Google Analytics (optional)
GOOGLE_ANALYTICS_MEASUREMENT_ID=
GOOGLE_ANALYTICS_PROPERTY_ID=
GOOGLE_APPLICATION_CREDENTIALS=config/ga4-service-account.json

# Deploy webhook (production only — leave empty locally)
WEBHOOK_SECRET=
DEPLOY_APP_DIR=/var/www/pokeAPI

# Operator scripts (production only — never commit real values)
PROD_SSH_HOST=
PROD_SSH_USER=root
PROD_DB_HOST=localhost
PROD_DB_PORT=5432
PROD_DB_NAME=pokeapi
PROD_DB_USER=pokeapi
PROD_DB_PASSWORD=
```

- [ ] **Step 2: Document copy step in README**

Add under Installation:

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY at minimum
```

- [ ] **Step 3: Verify example is not ignored**

```bash
git check-ignore -v .env.example || echo "OK: not ignored"
```

Expected: `OK: not ignored`

- [ ] **Step 4: Commit**

```bash
git add .env.example README.md
git commit -m "docs: add .env.example for local and Docker setup"
```

---

### Task 3: Remove production IP and paths from tracked files

**Files:**
- Modify: `README.md` (~line 171)
- Modify: `CLAUDE.md` (~lines 132–137)
- Modify: `docs/database_management.md` (lines 29, 387, 407, 415)
- Modify: `scripts/backup_db.py` (lines 235, 262, 306)
- Modify: `scripts/upload_pokemon_summaries.py` (lines 346, 372, 436)
- Modify: `scripts/download_pokemon_summaries.py` (lines 4, 167, 170)

- [ ] **Step 1: Replace doc SSH examples with placeholders**

In `README.md` and `docs/database_management.md`, replace:

```bash
ssh -L 5433:localhost:5432 root@149.28.243.132
```

With:

```bash
ssh -L 5433:localhost:5432 ${PROD_SSH_USER:-root}@${PROD_SSH_HOST:?set PROD_SSH_HOST in .env}
```

Add a short note: *Operator-only — set `PROD_SSH_HOST` in your private `.env`; not required for local/Docker use.*

- [ ] **Step 2: Refactor scripts to read SSH host from environment**

In `scripts/backup_db.py`, replace hardcoded connect:

```python
# Before
ssh.connect("149.28.243.132", username="root")

# After
import os
host = os.environ.get("PROD_SSH_HOST")
user = os.environ.get("PROD_SSH_USER", "root")
if not host:
    raise SystemExit("PROD_SSH_HOST is not set. Add it to .env (operator use only).")
ssh.connect(host, username=user)
```

Apply the same pattern to `scripts/upload_pokemon_summaries.py` and fix usage strings in `scripts/download_pokemon_summaries.py` (docstrings/examples use `your-server.example` not a real IP).

- [ ] **Step 3: Scrub `CLAUDE.md` deploy section**

Remove or replace production one-liners with:

```markdown
### Deploy (operator — private notes)

Production deploy commands live in gitignored `DEPLOYMENT.md` (or your private runbook). Never commit server IPs or secrets.
```

- [ ] **Step 4: Verify no IP remains in tracked files**

```bash
rg "149\.28\.243\.132" --glob '!DEPLOYMENT.md' .
```

Expected: no matches (or only in gitignored `DEPLOYMENT.md`).

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md docs/database_management.md scripts/
git commit -m "refactor: remove hardcoded production host from docs and scripts"
```

---

### Task 4: Parameterize deploy webhook paths

**Files:**
- Modify: `routes/webhook.py` (all `/var/www/pokeAPI` paths)
- Modify: `.env.example` (already has `DEPLOY_APP_DIR`)
- Test: `tests/` — add or extend test if webhook tests exist; else manual note

- [ ] **Step 1: Add deploy directory helper**

At top of `routes/webhook.py` after imports:

```python
def _deploy_app_dir() -> str:
    return os.getenv("DEPLOY_APP_DIR", "/var/www/pokeAPI")
```

- [ ] **Step 2: Replace hardcoded paths**

Replace every `"/var/www/pokeAPI"` with `_deploy_app_dir()` in `subprocess.run` git/pip/gunicorn commands (lines ~49–110).

- [ ] **Step 3: Run tests**

```bash
cd /Users/joereg4/pokeAPI
.venv/bin/pytest tests/ -q -m "not integration"
```

Expected: 480 passed (or current baseline).

- [ ] **Step 4: Commit**

```bash
git add routes/webhook.py
git commit -m "refactor: make webhook deploy path configurable via DEPLOY_APP_DIR"
```

---

### Task 5: Public `DEPLOYMENT.md` + private operator doc

**Files:**
- Create: `DEPLOYMENT.md` (tracked — public)
- Rename or copy: existing gitignored `DEPLOYMENT.md` → `DEPLOYMENT.private.md` (local only, add to `.gitignore`)
- Modify: `.gitignore`

- [ ] **Step 1: Preserve private content locally**

```bash
cd /Users/joereg4/pokeAPI
cp DEPLOYMENT.md DEPLOYMENT.private.md   # if DEPLOYMENT.md exists locally
```

- [ ] **Step 2: Update `.gitignore`**

Remove `DEPLOYMENT.md` from ignore list. Add:

```
# Operator-only (real IPs, production paths)
DEPLOYMENT.private.md
```

- [ ] **Step 3: Write public `DEPLOYMENT.md`**

Structure (no real IPs, no root passwords):

```markdown
# Deployment Guide

This document covers **self-hosted** deployment patterns. For a quick local site, use Docker (see README).

## Local development (recommended)

1. `cp .env.example .env` and set `SECRET_KEY`
2. `docker compose up --build` OR `.venv` + Postgres + Redis (README)
3. Open http://localhost:8080 (Docker) or http://127.0.0.1:5000 (Flask dev)

## Docker Compose (production-like local)

- Services: app, nginx, postgres, redis
- DB seed: `docker/db/seed.sql` (committed, sanitized)
- Env: `.env` (not committed)

## Bare-metal outline (bring your own server)

1. Provision: Python 3.9+, PostgreSQL, Redis, nginx
2. Clone repo; create venv; `pip install -r requirements.txt`
3. Set all variables from `.env.example`
4. `flask db upgrade`
5. Run gunicorn behind nginx (example unit files not included — adapt to your OS)
6. Optional: GitHub deploy webhook — set `WEBHOOK_SECRET` and `DEPLOY_APP_DIR`

## What not to commit

- `.env`, `*.sql` dumps, `config/ga4-service-account.json`
- Production hostnames or SSH details — use `DEPLOYMENT.private.md` locally

## Database migrations

\`\`\`bash
source .venv/bin/activate
flask db upgrade
\`\`\`
```

- [ ] **Step 4: Commit public deployment doc**

```bash
git add DEPLOYMENT.md .gitignore
git commit -m "docs: add public DEPLOYMENT.md; keep private notes in DEPLOYMENT.private.md"
```

---

### Task 6: Docker — clone-and-run for strangers

**Files:**
- Create: `docker/db/seed.sql`
- Modify: `docker-compose.yml`
- Modify: `docker/db/init.sh` (optional: prefer seed over backup)
- Create: `docker/README.md`
- Modify: `.dockerignore` (if tests should run in container — optional)
- Modify: `README.md` — Docker quick start

- [ ] **Step 1: Create sanitized `docker/db/seed.sql`**

Minimum viable seed (no real users — adjust to match your schema):

```sql
-- Minimal schema bootstrap for Docker; run flask migrations if you need full schema.
-- Prefer: empty DB + `docker compose run --rm app flask db upgrade`
-- Plus optional demo admin created via manage.py in README.

-- If backup.sql was only data: document that newcomers should use migrations + manage.py create_user
```

**Recommended approach:** Empty init + document:

```bash
docker compose up -d db redis
docker compose run --rm app flask db upgrade
docker compose run --rm app python manage.py create_user
docker compose up -d
```

If you need faster first-run with data, export a **sanitized** subset (no `users` table rows, no emails) from staging.

- [ ] **Step 2: Update `docker-compose.yml`**

```yaml
  nginx:
    ports:
      - "${NGINX_PORT:-8080}:80"

  app:
    environment:
      - FLASK_ENV=${FLASK_ENV:-development}
    ports:
      - "8000:8000"   # optional: direct app access for smoke tests

  db:
    volumes:
      - ./docker/db/seed.sql:/docker-entrypoint-initdb.d/seed.sql:ro
      # Remove backup.sql mount from default compose — document in docker/README.md
```

- [ ] **Step 3: Add `docker/README.md`**

Include:

- Prerequisites: Docker, `cp .env.example .env`
- `docker compose up --build`
- URL: `http://localhost:8080`
- Port 80 conflict: set `NGINX_PORT=8080`
- No `backup.sql` in repo — how to use migrations
- `docker compose down -v` to reset DB

- [ ] **Step 4: Smoke test**

```bash
docker compose down -v
docker compose up --build -d
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
```

Expected: `200`

- [ ] **Step 5: Commit**

```bash
git add docker/ docker-compose.yml README.md
git commit -m "feat(docker): public clone-and-run with seed and configurable nginx port"
```

---

### Task 7: README overhaul

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Remove or move stale UI changelog**

Move lines 1–36 (item display / move category notes) to `docs/CHANGELOG-ui.md` or delete if obsolete.

- [ ] **Step 2: Add prominent Quick Start (Docker)**

```markdown
## Quick Start (Docker)

\`\`\`bash
git clone https://github.com/<your-org>/pokeAPI.git
cd pokeAPI
cp .env.example .env
# Edit .env: set SECRET_KEY
docker compose up --build
\`\`\`

Open **http://localhost:8080**. See [DEPLOYMENT.md](DEPLOYMENT.md) and [docker/README.md](docker/README.md).

## Quick Start (local Python)

\`\`\`bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Start Postgres + Redis, set DATABASE_URL and REDIS_URL
.venv/bin/flask db upgrade
.venv/bin/python manage.py create_user
.venv/bin/python app.py
\`\`\`
```

- [ ] **Step 3: Fix venv naming**

Replace `venv` with `.venv` throughout Setup section.

- [ ] **Step 4: Split "Database Management"**

Keep script **names** but add banner:

> **Operator tools** — require `PROD_SSH_HOST` and production DB access. Not needed to run a local Pokédex.

- [ ] **Step 5: Add License + Security links**

Point to `LICENSE` (add if missing) and `SECURITY.md`.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/CHANGELOG-ui.md
git commit -m "docs: rewrite README for public clone-and-run onboarding"
```

---

### Task 8: CI and GitHub repo hygiene

**Files:**
- Modify: `.github/workflows/ci.yml` (only if webhook URL is hardcoded — use secrets)
- Create: `SECURITY.md`
- Create: `LICENSE` (if absent — user chooses MIT/Apache-2.0)
- Create: `CONTRIBUTING.md` (short)

- [ ] **Step 1: Verify CI uses secrets for deploy webhook**

In `.github/workflows/ci.yml`, ensure production URL is `${{ secrets.DEPLOY_WEBHOOK_URL }}` or skip deploy step on forks. Document required secrets in `CONTRIBUTING.md` — no URLs with your domain in repo if you want zero infra leakage (optional: keep `pokedexapi.com` only in private CI secrets description).

- [ ] **Step 2: Add `SECURITY.md`**

```markdown
# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| main    | Yes       |

## Reporting a vulnerability

Please report security issues via GitHub Security Advisories (private report) or email [your-public-contact].

Do not open public issues for undisclosed vulnerabilities.
```

- [ ] **Step 3: Enable GitHub features (manual, on github.com)**

- [ ] Secret scanning + push protection
- [ ] Private vulnerability reporting
- [ ] Branch protection on `main` (require CI)

- [ ] **Step 4: Commit policy files**

```bash
git add SECURITY.md CONTRIBUTING.md LICENSE
git commit -m "docs: add security policy and contributing guide"
```

---

### Task 9: Production safety in app config

**Files:**
- Modify: `app.py` (~line 99)

- [ ] **Step 1: Fail closed on production without SECRET_KEY**

```python
secret = os.environ.get("SECRET_KEY")
env = pokedex.env.get_env_variable("FLASK_ENV", "production")
if env == "production" and not secret:
    raise RuntimeError("SECRET_KEY must be set when FLASK_ENV=production")
app.config["SECRET_KEY"] = secret or "dev"
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/pytest tests/ -q -m "not integration"
```

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "fix: require SECRET_KEY in production"
```

---

### Task 10: Final verification before `public`

**Files:** none new

- [ ] **Step 1: Full test suite**

```bash
.venv/bin/pytest tests/ -q -m "not integration"
```

- [ ] **Step 2: Docker smoke**

```bash
docker compose up --build -d && curl -sf http://localhost:8080/ > /dev/null && echo OK
```

- [ ] **Step 3: Re-run gitleaks**

```bash
gitleaks detect --source . --verbose
```

Expected: clean (or documented accepted false positives)

- [ ] **Step 4: Public-repo checklist (sign off)**

- [ ] No `149.28.243.132` in tracked files
- [ ] `.env.example` committed; `.env` not tracked
- [ ] No real users in committed SQL
- [ ] `DEPLOYMENT.md` is public-safe; private notes in `DEPLOYMENT.private.md` (gitignored)
- [ ] README Docker path works on fresh clone
- [ ] Rotate keys if gitleaks/history ever exposed `.env` or API keys
- [ ] GitHub: secret scanning enabled

- [ ] **Step 5: Open PR `chore/public-repo-prep` for review**

---

## Self-review (plan vs spec)

| User requirement | Task |
|------------------|------|
| Public-safe deployment doc | Task 5 |
| Remove IPs / private infra from repo | Task 3, 8 |
| Clone & run locally | Task 6, 7 |
| Solid README/docs | Task 7, 5, `docker/README.md` |
| Secrets protected; users bring own | Task 2, 1, 10 |
| Docker test path | Task 6, 10 |

**Placeholder scan:** No TBD implementation steps — operator SQL seed content depends on your schema (documented choice: migrations + `create_user`).

---

## Suggested implementation order

1. Task 1 (scan) → 2 (`.env.example`) → 3 (scrub IPs) → 4 (webhook)
2. Task 5–6 (docs + Docker) in parallel if two people
3. Task 7 (README) → 8 (GitHub hygiene) → 9 (SECRET_KEY) → 10 (verify)

**Estimated effort:** 1–2 focused days; +extra if git history needs secret purge.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-05-30-public-repo-prep.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — one subagent per task, review between tasks  
2. **Inline Execution** — implement in this session with checkpoints after Tasks 1, 6, and 10

Which approach do you want?

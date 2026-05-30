# Dead-End Route Audit

This document records routes that are registered in the Flask application but
are **not reachable** through any in-app link, button, redirect, or navigation
element.  Users can only reach them by typing the URL directly or, for some
detail pages, through the search bar.

## How to run the audit

```bash
# Human-readable report
python3 scripts/find_dead_end_routes.py

# Machine-readable JSON
python3 scripts/find_dead_end_routes.py --json
```

The script loads the Flask app, enumerates every registered endpoint via
`app.url_map`, then scans all templates and Python source files for
`url_for(...)` calls.  Any endpoint that is never referenced is a candidate
dead end.

## Current findings

*Last updated: 2026-02-14*

### Fixes applied

The following navigation improvements were made to eliminate major dead ends:

1. **Moves** and **Items** added as direct links in the main navbar
   (`base.html`).
2. **Browse dropdown** added to the navbar grouping: Colors, Habitats, Shapes,
   Locations, Regions, Berries, Generations, Egg Groups, and Characteristics.
3. **Moves and Items counts** added to the home page statistics section
   (`index.html`, `routes/pokemon.py`).
4. **Documentation link** added to the admin dashboard under System Health
   (`admin/dashboard.html`).

### Remaining dead ends: none (as of 2026-02-14)

The 17 previously unlinked detail-only routes were **removed** as dedicated
Flask routes.  Their URLs are still served by the catch-all
`utilities.get_endpoint_data` (route `/<api_endpoint>/<id_or_name>`): when
`api_endpoint` is in `pokedex.__all__` and the utilities module has no
dedicated view for it, the app fetches via `APIResource.fetch_data` and
renders `generic.html` (catch-all only; stat, encounter-method, contest-type, and item-category have dedicated templates).  So:

- **Search and direct URLs** (e.g. `/evolution-chain/1`, `/pokemon-form/bulbasaur`)
  still work.
- **No** `url_for` links to those endpoints (they are no longer separate
  endpoints), so the dead-end script reports 0 true dead ends.

### Intentional / API-only (not UX problems)

These endpoints are unlinked by design — they serve APIs, internal tooling,
or are reached by hardcoded hrefs:

| Endpoint | URL Pattern | Reason |
|----------|-------------|--------|
| `pokemon.index` | `/` | Linked via hardcoded `href="/"` in nav |
| `search.search_resources` | `/api/search` | Called by JavaScript search |
| `sprite.get_specific_sprite` | `/<pokemon_id>/<sprite_type>` | Called programmatically |

### Reachable via search only

Detail pages for resource types stored in the `Resource` database table
(pokemon, ability, item, move, type, etc.) **are** reachable through the
navbar search bar.  The search generates `/{type}/{name}` URLs that are
handled by `utilities.get_endpoint_data`.  These are not dead ends but lack
direct navigation.

## Audit: Are the "utilities" and other dead ends actually used?

*Audit date: 2026-02-14*

The script only detects **`url_for('endpoint_name')`** in templates and Python.
It does **not** detect:

- Hardcoded `href="/path"` URLs
- JavaScript-built URLs (e.g. search uses `'/' + type + '/' + name`)
- Python calls to **data-fetching** (e.g. `pokedex.APIResource.fetch_data(...)` or loaders in `pokedex/loaders.py`)

Findings:

1. **Script is correct**  
   None of the 18 true dead-end endpoints are referenced by any `url_for(...)` in the repo. So they are correctly classified as "no in-app link."

2. **"Utilities" confusion**  
   - **Flask routes** in `routes/utilities.py` (e.g. `get_encounter_condition`, `get_language`) are **web UI** routes: they serve HTML pages for that data. No template or Python code uses `url_for('utilities.get_encounter_condition', ...)`, so the script correctly marks them as dead.  
   - **Pokedex "utilities"** in `pokedex/loaders.py` (e.g. `fetch_data("encounter-condition", ...)`) are **data lookups** (PokeAPI/cache). They do not call Flask routes; they are used by other Python code. So the script is not wrong: the Flask routes and the loaders are separate. The dead-end report is about **navigational links**, not about whether the underlying data is used.

3. **Search bar**  
   Search builds URLs like `/evolution-chain/1` in JavaScript. The browser then requests that URL. Flask routes it to the **specific** view (e.g. `evolution_growth.get_evolution_chain`) when the rule is more specific than the catch-all `utilities.get_endpoint_data`. So those pages are reachable via search, but they are still "unlinked" in the sense that no `url_for` points to them. The script does not (and need not) follow JS-built URLs.

4. **Bug found: machine pagination**  
   `templates/machine.html` uses `url_for('pokemon.get_machines', ...)` for pagination, but **`pokemon.get_machines` does not exist**. The machine list and pagination are implemented in `abilities_moves_items.get_machines`. So:
   - The script marks `abilities_moves_items.get_machines` as a dead end (no `url_for` to it).
   - The template actually references a non-existent endpoint (`pokemon.get_machines`), which would cause `BuildError` when rendering the machine page.  
   **Fix:** Use `abilities_moves_items.get_machines` in `machine.html`. That both fixes the bug and adds the missing link for the script.

## Future recommendations

To add **cross-links** from parent detail views to these resource types, use
`url_for('utilities.get_endpoint_data', api_endpoint='evolution-chain', id_or_name=id)`
(or the appropriate `api_endpoint` and `id_or_name`).  For example:

- **Move detail** → link to move-ailment, move-target, move-battle-style when present.
- **Item detail** → link to item-fling-effect, item-pocket.
- **Pokemon detail** → link to pokemon-form, growth-rate, nature, evolution-chain.
- **Berry detail** → link to super-contest-effect.
- **Region/Location detail** → link to pal-park-area, encounter-condition.

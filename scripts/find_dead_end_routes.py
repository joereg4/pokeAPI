#!/usr/bin/env python3
"""
Detect dead-end routes in the Pokédex Flask application.

A "dead-end route" is one that is registered in the Flask app but never
linked to from any template (url_for), Python redirect, or navigation
element.  Users can only reach these pages by typing the URL directly.

How it works
------------
1. Loads the Flask app and enumerates every registered endpoint from
   ``app.url_map``.
2. Scans all Jinja2 templates (``templates/**/*.html``) and Python source
   files (``routes/**/*.py``, ``app.py``, ``pokedex/**/*.py``) for
   ``url_for('...')`` calls and extracts the endpoint argument.
3. Compares the two sets: any endpoint that is never referenced by a
   ``url_for`` call is a candidate dead end.
4. Classifies candidates into categories:
   - **True dead ends** – list/index pages with no link from the UI
   - **Search-only** – detail pages reachable only via the search bar
   - **Intentional / API-only** – health checks, webhooks, search API, etc.

Usage
-----
    python3 scripts/find_dead_end_routes.py          # human-readable report
    python3 scripts/find_dead_end_routes.py --json    # machine-readable JSON

Requirements
------------
Must be run from the project root so that ``app.py`` and ``templates/`` are
importable/accessible.

Rationale
---------
Keeping an up-to-date picture of route reachability prevents UX blind spots
where functional pages exist but no user can ever navigate to them.
"""

import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Directories / files to scan for url_for references
TEMPLATE_DIR = "templates"
TEMPLATE_GLOB = "**/*.html"
PYTHON_SCAN_PATHS = [
    "routes",
    "app.py",
    "pokedex",
]

# Regex to extract the first argument of url_for('endpoint_name', ...)
# Handles both single and double quotes, and optional keyword arguments.
URL_FOR_RE = re.compile(r"""url_for\(\s*['"]([a-zA-Z_][a-zA-Z0-9_.]+)['"]""")

# Endpoints that are intentionally not linked from the UI.
# They are API-only, infrastructure, or internal – not UX dead ends.
INTENTIONAL_ENDPOINTS = {
    # Home page – linked via hardcoded href="/" in the nav bar, not url_for
    "pokemon.index",
    # Search API – consumed by JavaScript, not via url_for in templates
    "search.search_resources",
    # Webhook – called by external services
    "webhook.webhook",
    # Sprite helpers – called programmatically in Python
    "sprite.get_artwork",
    "sprite.get_default_sprite",
    "sprite.get_specific_sprite",
    # Health endpoints (linked from admin dashboard)
    "health.check_cache_health",
    "health.health_cache_json",
    # Flask built-in static endpoint
    "static",
    "pokemon.static",
    "abilities_moves_items.static",
    "locations_regions.static",
    "evolution_growth.static",
    "characteristics_stats.static",
    "berries_contests.static",
    "breeding.static",
}

# Rate-limit exempt placeholder routes defined in app.py that simply ``pass``
# and are overridden by the real blueprint routes.  They register as
# separate endpoints but never serve real content.
APP_EXEMPT_PLACEHOLDERS = {
    "exempt_artwork",
    "exempt_pokemon_list",
    "exempt_type_pokemon_list",
    "exempt_pokedex_detail",
    "exempt_ability_detail",
    "exempt_move_detail",
    "exempt_item_detail",
    "exempt_pokemon_species",
    "exempt_pokemon_color",
    "exempt_pokemon_habitat",
    "exempt_pokemon_shape",
}

# Test-only routes (only registered when TESTING=True)
TEST_ONLY_ENDPOINTS = {
    "test_403",
    "test_404",
    "test_500",
    "test_429",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def collect_registered_endpoints(app):
    """Return a dict of ``{endpoint_name: url_rule}`` from the Flask app."""
    endpoints = {}
    for rule in app.url_map.iter_rules():
        ep = rule.endpoint
        # Skip built-in static, test-only, and placeholder endpoints
        if ep in APP_EXEMPT_PLACEHOLDERS or ep in TEST_ONLY_ENDPOINTS:
            continue
        if ep.endswith(".static"):
            continue
        if ep == "static":
            continue
        endpoints[ep] = rule.rule
    return endpoints


def scan_file_for_url_for(filepath):
    """Return a set of endpoint names referenced via ``url_for`` in *filepath*."""
    found = set()
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                for match in URL_FOR_RE.finditer(line):
                    found.add(match.group(1))
    except (OSError, IOError):
        pass
    return found


def collect_linked_endpoints(project_root):
    """Walk templates and Python files, returning all url_for targets."""
    linked = set()

    # --- Templates ---
    tpl_dir = os.path.join(project_root, TEMPLATE_DIR)
    if os.path.isdir(tpl_dir):
        for dirpath, _dirs, filenames in os.walk(tpl_dir):
            for fname in filenames:
                if fname.endswith(".html"):
                    linked |= scan_file_for_url_for(os.path.join(dirpath, fname))

    # --- Python source ---
    for rel_path in PYTHON_SCAN_PATHS:
        abs_path = os.path.join(project_root, rel_path)
        if os.path.isfile(abs_path):
            linked |= scan_file_for_url_for(abs_path)
        elif os.path.isdir(abs_path):
            for dirpath, _dirs, filenames in os.walk(abs_path):
                for fname in filenames:
                    if fname.endswith(".py"):
                        linked |= scan_file_for_url_for(
                            os.path.join(dirpath, fname)
                        )

    return linked


def classify_dead_ends(dead_ends, registered):
    """
    Separate dead-end endpoints into three buckets:

    1. ``intentional`` – API / infrastructure routes (from INTENTIONAL_ENDPOINTS)
    2. ``search_only`` – detail pages reachable via the search bar
       (search builds ``/{type}/{name}`` → ``utilities.get_endpoint_data``)
    3. ``true_dead_ends`` – pages with **no** in-app path to reach them
    """
    intentional = set()
    true_dead_ends = {}

    for ep in sorted(dead_ends):
        url = registered.get(ep, "")
        if ep in INTENTIONAL_ENDPOINTS:
            intentional.add(ep)
        else:
            true_dead_ends[ep] = url

    return {
        "intentional": sorted(intentional),
        "true_dead_ends": true_dead_ends,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    # Determine project root (parent of scripts/)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, project_root)
    os.chdir(project_root)

    # Import and create the Flask app
    from app import create_app

    app = create_app()

    with app.app_context():
        # Step 1: Enumerate registered endpoints
        registered = collect_registered_endpoints(app)

        # Step 2: Collect every url_for target from templates and Python
        linked = collect_linked_endpoints(project_root)

        # Step 3: Find endpoints that are registered but never linked
        dead_ends = set(registered.keys()) - linked

        # Step 4: Classify
        classification = classify_dead_ends(dead_ends, registered)

        # ------------------------------------------------------------------
        # Output
        # ------------------------------------------------------------------
        if "--json" in sys.argv:
            print(
                json.dumps(
                    {
                        "total_registered": len(registered),
                        "total_linked": len(linked),
                        "dead_end_count": len(dead_ends),
                        "classification": {
                            "intentional": classification["intentional"],
                            "true_dead_ends": classification["true_dead_ends"],
                        },
                        "all_registered_endpoints": {
                            ep: url for ep, url in sorted(registered.items())
                        },
                        "all_linked_endpoints": sorted(linked),
                    },
                    indent=2,
                )
            )
            return

        # Human-readable output
        print("=" * 70)
        print("  DEAD-END ROUTE AUDIT")
        print("=" * 70)
        print(f"  Registered endpoints : {len(registered)}")
        print(f"  Linked endpoints     : {len(linked)}")
        print(f"  Unlinked (dead ends) : {len(dead_ends)}")
        print()

        # True dead ends
        true_de = classification["true_dead_ends"]
        if true_de:
            print("-" * 70)
            print("  TRUE DEAD ENDS (no link anywhere in the app)")
            print("-" * 70)
            for ep, url in sorted(true_de.items()):
                print(f"    {ep:<55s} {url}")
            print()

        # Intentional / API-only
        intent = classification["intentional"]
        if intent:
            print("-" * 70)
            print("  INTENTIONAL / API-ONLY (not a UX problem)")
            print("-" * 70)
            for ep in intent:
                url = registered.get(ep, "")
                print(f"    {ep:<55s} {url}")
            print()

        # Summary
        print("=" * 70)
        print(f"  Action needed: {len(true_de)} route(s) should be linked or removed.")
        print("=" * 70)


if __name__ == "__main__":
    main()

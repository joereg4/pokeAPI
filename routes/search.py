# routes/search.py
"""
Dedicated search API backed by PostgreSQL.

Provides a JSON endpoint for the navbar autocomplete search. Queries the
Resource table directly so results always reflect the current database state
(no stale static files or long-lived caches).

Short-lived per-query caching (10 s) reduces DB load for repeated keystrokes
while keeping results fresh.
"""
import logging
from flask import Blueprint, jsonify, request
from models.model import Resource
from cache import cache
from limiter import limiter

search_bp = Blueprint("search", __name__)

# Maximum number of suggestions returned per request
MAX_RESULTS = 10

# Per-query cache TTL in seconds (short – keeps results fresh)
SEARCH_CACHE_TTL = 10


@search_bp.route("/api/search")
@limiter.limit("60 per minute")
def search_resources():
    """
    Search resources by name.

    Query params:
        q     – search term (required, min 1 char)
        limit – max results to return (optional, default 10, max 50)

    Returns JSON array:
        [{"name": "pikachu", "type": "pokemon"}, ...]

    Ranking: exact prefix matches appear before substring-only matches so
    typing "pik" ranks "pikachu" above "spike" or "togepi-kachu".
    """
    term = request.args.get("q", "").strip().lower()
    if not term:
        return jsonify([])

    # Clamp the requested limit
    try:
        limit = min(int(request.args.get("limit", MAX_RESULTS)), 50)
    except (ValueError, TypeError):
        limit = MAX_RESULTS

    # Try cache first (key includes the normalised term + limit)
    cache_key = f"search:{term}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        # Strategy: fetch prefix matches first, then substring matches,
        # and merge them so prefix hits are ranked higher.
        prefix_results = (
            Resource.query
            .filter(Resource.name.ilike(f"{term}%"))
            .order_by(Resource.name)
            .limit(limit)
            .all()
        )

        # Only fetch substring matches if we haven't filled the limit
        remaining = limit - len(prefix_results)
        substring_results = []
        if remaining > 0:
            substring_results = (
                Resource.query
                .filter(
                    Resource.name.ilike(f"%{term}%"),
                    # Exclude prefix matches we already have
                    ~Resource.name.ilike(f"{term}%"),
                )
                .order_by(Resource.name)
                .limit(remaining)
                .all()
            )

        # Build the combined result list
        results = [
            {"name": r.name, "type": r.resource}
            for r in prefix_results + substring_results
        ]

        # Only cache non-empty results so that a miss for a new prefix
        # doesn't get stuck returning [] after data is inserted.
        if results:
            cache.set(cache_key, results, timeout=SEARCH_CACHE_TTL)

        return jsonify(results)

    except Exception as e:
        logging.error(f"Search query failed: {e}")
        return jsonify([]), 500

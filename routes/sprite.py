# routes/sprite.py
"""Sprite routes for serving Pokemon images.

Architecture:
    - Artwork route resolves form IDs -> species IDs via the cached resolver.
    - When a sprite genuinely doesn't exist upstream, serves a styled placeholder
      image instead of a JSON error (prevents broken <img> tags on the frontend).
    - All successful responses include long-lived cache headers.
"""

from flask import Blueprint, jsonify, send_file, url_for, make_response
from pokedex.api import get_sprite
from pokedex.common import sprite_url_build
from pokedex.species_resolver import resolve_species_id
from pokedex.utils import Config
from limiter import limiter
import logging
import os
from datetime import datetime, timedelta

sprite_bp = Blueprint("sprite", __name__, url_prefix="/sprite")

VALID_SPRITES = Config.VALID_SPRITES

# Path to the placeholder image served when a sprite is missing upstream.
_PLACEHOLDER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "img", "default_pokemon.png",
)


def _add_cache_headers(response, max_age=31536000):
    """Add cache control headers to the response.

    Args:
        response: Flask response object.
        max_age: Cache duration in seconds (default 1 year for sprites).
    """
    response.headers["Cache-Control"] = f"public, max-age={max_age}"
    response.headers["Expires"] = (
        datetime.utcnow() + timedelta(seconds=max_age)
    ).strftime("%a, %d %b %Y %H:%M:%S GMT")
    return response


def _serve_sprite(sprite_data):
    """Serve sprite data as a PNG response with cache headers.

    If sprite_data is None or missing a path, serves the placeholder.
    """
    if sprite_data and "path" in sprite_data:
        response = make_response(
            send_file(sprite_data["path"], mimetype="image/png")
        )
        return _add_cache_headers(response)

    return _serve_placeholder()


def _serve_placeholder():
    """Serve the placeholder image with short cache (1 hour).

    Uses a shorter cache TTL than real sprites because the upstream sprite
    may become available later (e.g., after a PokeAPI data update).
    """
    if os.path.exists(_PLACEHOLDER_PATH):
        response = make_response(
            send_file(_PLACEHOLDER_PATH, mimetype="image/png")
        )
        return _add_cache_headers(response, max_age=3600)

    # Last resort: if even the placeholder is missing
    return jsonify({"error": "Sprite not found"}), 404


@sprite_bp.route("/artwork/<pokemon_id>")
@limiter.exempt
def get_artwork(pokemon_id):
    """Get the official artwork for a Pokemon.

    Resolves form IDs (>= 10000) to their species ID via the Redis-cached
    species resolver so artwork does not 404.  Serves a placeholder if the
    sprite genuinely doesn't exist upstream.
    """
    try:
        artwork_id = resolve_species_id(pokemon_id)
        sprite_data = get_sprite(
            "pokemon", artwork_id, other=True, official_artwork=True
        )
        return _serve_sprite(sprite_data)
    except Exception as e:
        logging.error(f"Error fetching artwork for Pokemon {pokemon_id}: {e}")
        return _serve_placeholder()


@sprite_bp.route("/default/<pokemon_id>")
@limiter.exempt
def get_default_sprite(pokemon_id):
    """Get the default front sprite for a Pokemon.

    Serves a placeholder when the upstream sprite is missing.
    """
    try:
        sprite_data = get_sprite("pokemon", pokemon_id)
        return _serve_sprite(sprite_data)
    except Exception as e:
        logging.error(f"Error fetching default sprite for Pokemon {pokemon_id}: {e}")
        return _serve_placeholder()


@sprite_bp.route("/<pokemon_id>/<sprite_type>")
@limiter.exempt
def get_specific_sprite(pokemon_id, sprite_type):
    """Get a specific sprite variant for a Pokemon.

    Returns 400 for invalid sprite types, and serves a placeholder when
    the requested variant doesn't exist upstream.
    """
    if sprite_type not in VALID_SPRITES:
        return jsonify({"error": "Invalid sprite type"}), 400

    options = {}
    if "back" in sprite_type:
        options["back"] = True
    if "shiny" in sprite_type:
        options["shiny"] = True
    if "female" in sprite_type:
        options["female"] = True

    try:
        sprite_data = get_sprite("pokemon", pokemon_id, **options)
        return _serve_sprite(sprite_data)
    except Exception as e:
        logging.error(
            f"Error fetching {sprite_type} sprite for Pokemon {pokemon_id}: {e}"
        )
        return _serve_placeholder()


def get_sprite_url(pokemon_id, sprite_type=None, is_artwork=False):
    """Helper function to generate sprite URLs for templates."""
    if is_artwork:
        return url_for("sprite.get_artwork", pokemon_id=pokemon_id, _external=False)
    elif sprite_type in VALID_SPRITES:
        return url_for(
            "sprite.get_specific_sprite",
            pokemon_id=pokemon_id,
            sprite_type=sprite_type,
            _external=False,
        )
    else:
        return url_for(
            "sprite.get_default_sprite", pokemon_id=pokemon_id, _external=False
        )

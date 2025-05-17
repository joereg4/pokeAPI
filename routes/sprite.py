from flask import Blueprint, jsonify, send_file, url_for, make_response
from pokedex.api import get_sprite
from pokedex.common import sprite_url_build
from pokedex.utils import Config
from limiter import limiter
import logging
import os
from datetime import datetime, timedelta

sprite_bp = Blueprint("sprite", __name__)

VALID_SPRITES = Config.VALID_SPRITES


def add_cache_headers(response):
    """Add cache control headers to the response"""
    response.headers["Cache-Control"] = "public, max-age=31536000"  # Cache for 1 year
    response.headers["Expires"] = (datetime.utcnow() + timedelta(days=365)).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )
    return response


@sprite_bp.route("/artwork/<pokemon_id>")
@limiter.exempt
def get_artwork(pokemon_id):
    """Get the official artwork for a Pokémon."""
    try:
        sprite_data = get_sprite(
            "pokemon", pokemon_id, other=True, official_artwork=True
        )
        if not sprite_data or "path" not in sprite_data:
            return jsonify({"error": "Artwork not found"}), 404
        response = make_response(send_file(sprite_data["path"], mimetype="image/png"))
        return add_cache_headers(response)
    except Exception as e:
        logging.error(f"Error fetching artwork for Pokémon {pokemon_id}: {e}")
        return jsonify({"error": str(e)}), 500


@sprite_bp.route("/default/<pokemon_id>")
@limiter.exempt
def get_default_sprite(pokemon_id):
    """Get the default front sprite for a Pokémon."""
    try:
        sprite_data = get_sprite("pokemon", pokemon_id)
        if not sprite_data or "path" not in sprite_data:
            return jsonify({"error": "Sprite not found"}), 404
        response = make_response(send_file(sprite_data["path"], mimetype="image/png"))
        return add_cache_headers(response)
    except Exception as e:
        logging.error(f"Error fetching default sprite for Pokémon {pokemon_id}: {e}")
        return jsonify({"error": str(e)}), 500


@sprite_bp.route("/<pokemon_id>/<sprite_type>")
@limiter.exempt
def get_specific_sprite(pokemon_id, sprite_type):
    """Get a specific sprite variant for a Pokémon."""
    try:
        if sprite_type not in VALID_SPRITES:
            return jsonify({"error": "Invalid sprite type"}), 400

        # Parse the sprite type to set correct options
        options = {}
        if "back" in sprite_type:
            options["back"] = True
        if "shiny" in sprite_type:
            options["shiny"] = True
        if "female" in sprite_type:
            options["female"] = True

        sprite_data = get_sprite("pokemon", pokemon_id, **options)
        if not sprite_data or "path" not in sprite_data:
            return jsonify({"error": "Sprite not found"}), 404
        response = make_response(send_file(sprite_data["path"], mimetype="image/png"))
        return add_cache_headers(response)
    except Exception as e:
        logging.error(
            f"Error fetching {sprite_type} sprite for Pokémon {pokemon_id}: {e}"
        )
        return jsonify({"error": str(e)}), 500


def get_sprite_url(pokemon_id, sprite_type=None, is_artwork=False):
    """Helper function to generate sprite URLs for templates"""
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

from flask import Blueprint, jsonify, send_file, url_for
from pokedex.api import get_sprite
from pokedex.common import sprite_url_build
from pokedex.utils import Config
import logging
import os

sprite_bp = Blueprint("sprite", __name__)

VALID_SPRITES = Config.VALID_SPRITES


@sprite_bp.route("/artwork/<pokemon_id>")
def get_artwork(pokemon_id):
    """Get the official artwork for a Pokémon."""
    try:
        sprite_data = get_sprite(
            "pokemon", pokemon_id, other=True, official_artwork=True
        )
        if not sprite_data or "path" not in sprite_data:
            return jsonify({"error": "Artwork not found"}), 404
        return send_file(sprite_data["path"], mimetype="image/png")
    except Exception as e:
        logging.error(f"Error fetching artwork for Pokémon {pokemon_id}: {e}")
        return jsonify({"error": str(e)}), 500


@sprite_bp.route("/default/<pokemon_id>")
def get_default_sprite(pokemon_id):
    """Get the default front sprite for a Pokémon."""
    try:
        sprite_data = get_sprite("pokemon", pokemon_id)
        if not sprite_data or "path" not in sprite_data:
            return jsonify({"error": "Sprite not found"}), 404
        return send_file(sprite_data["path"], mimetype="image/png")
    except Exception as e:
        logging.error(f"Error fetching default sprite for Pokémon {pokemon_id}: {e}")
        return jsonify({"error": str(e)}), 500


@sprite_bp.route("/<pokemon_id>/<sprite_type>")
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
        return send_file(sprite_data["path"], mimetype="image/png")
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


@sprite_bp.route("/test/<pokemon_id>")
def test_sprite(pokemon_id):
    """Test endpoint to examine sprite functionality for all variants."""
    try:
        results = {}
        # Test default sprite
        sprite_data = get_sprite("pokemon", pokemon_id)
        results["default"] = bool(sprite_data and "path" in sprite_data)

        # Test artwork
        sprite_data = get_sprite(
            "pokemon", pokemon_id, other=True, official_artwork=True
        )
        results["artwork"] = bool(sprite_data and "path" in sprite_data)

        # Test all sprite variants
        for sprite_type in VALID_SPRITES:
            sprite_data = get_sprite("pokemon", pokemon_id, sprite_type=sprite_type)
            results[sprite_type] = bool(sprite_data and "path" in sprite_data)

        return jsonify(results)
    except Exception as e:
        logging.error(f"Error testing sprites for Pokémon {pokemon_id}: {e}")
        return jsonify({"error": str(e)}), 500


@sprite_bp.route("/test-view-sprite/<pokemon_id>/<variant>")
def test_view_sprite(pokemon_id, variant):
    """Test endpoint to view different sprite variants"""
    try:
        options = {}

        if variant == "artwork":
            options["other"] = True
            options["official_artwork"] = True
        else:
            if "back" in variant:
                options["back"] = True
            if "shiny" in variant:
                options["shiny"] = True

        sprite_data = get_sprite("pokemon", pokemon_id, **options)
        if not sprite_data or "path" not in sprite_data:
            return jsonify({"error": f"Sprite not found for variant {variant}"}), 404

        return send_file(sprite_data["path"], mimetype="image/png")
    except Exception as e:
        logging.exception("Error in test_view_sprite endpoint")
        return jsonify({"error": str(e)}), 500

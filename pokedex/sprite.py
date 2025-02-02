import os
import logging
from flask import url_for
from .utils import Config

VALID_SPRITES = Config.VALID_SPRITES


def get_sprite_url(pokemon_id, sprite_type=None, is_artwork=False):
    """Generate the URL for a Pokemon sprite.

    Args:
        pokemon_id (int): The Pokemon's ID
        sprite_type (str, optional): The type of sprite (front_default, back_default, etc.)
        is_artwork (bool): Whether to get the official artwork instead of a sprite

    Returns:
        str: The URL for the sprite
    """
    if is_artwork:
        return url_for("sprite.get_artwork", pokemon_id=pokemon_id)
    elif sprite_type:
        return url_for(
            "sprite.get_specific_sprite", pokemon_id=pokemon_id, sprite_type=sprite_type
        )
    else:
        return url_for("sprite.get_default_sprite", pokemon_id=pokemon_id)

from __future__ import annotations

from typing import Optional, Union

from flask import url_for

from .utils import Config

VALID_SPRITES: list[str] = Config.VALID_SPRITES


def get_sprite_url(
    pokemon_id: Union[int, str],
    sprite_type: Optional[str] = None,
    is_artwork: bool = False,
) -> str:
    """Generate the URL for a Pokemon sprite.

    Args:
        pokemon_id: The Pokemon's ID or name.
        sprite_type: The type of sprite (front_default, back_default, etc.).
        is_artwork: Whether to get the official artwork instead of a sprite.

    Returns:
        Flask ``url_for`` path to the appropriate sprite endpoint.
    """
    if is_artwork:
        return url_for("sprite.get_artwork", pokemon_id=pokemon_id)
    elif sprite_type:
        return url_for(
            "sprite.get_specific_sprite", pokemon_id=pokemon_id, sprite_type=sprite_type
        )
    else:
        return url_for("sprite.get_default_sprite", pokemon_id=pokemon_id)

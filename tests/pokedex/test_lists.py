"""
Tests for pokedex.lists.

Verifies that official-artwork is requested by species id (not form id)
so upstream 404s are avoided for form/variant Pokémon (issue #38).
"""
import pytest
from unittest.mock import patch, MagicMock

from pokedex.lists import PokemonList, get_species_id_from_url


# Species URL format from PokeAPI (id at end of path)
SPECIES_URL_1027 = "https://pokeapi.co/api/v2/pokemon-species/1027/"


def test_official_artwork_uses_species_id_for_form_pokemon():
    """
    When add_pokemon_to_list receives a form Pokémon (pokemon id != species id),
    get_sprite must be called with species id for official_artwork=True.
    That way we never request upstream by form id, so the 404 is gone.
    """
    # Form Pokémon: koraidon-limited-build has pokemon id 1026, species id 1027
    form_pokemon = {
        "id": 1026,
        "name": "koraidon-limited-build",
        "species": {"name": "koraidon", "url": SPECIES_URL_1027},
        "sprites": {"other": {"official-artwork": {"front_default": None}}},
        "types": [],
    }
    pl = PokemonList({})
    pl.pokemon_list = []

    with patch("pokedex.lists.get_sprite") as mock_get_sprite:
        with patch("pokedex.lists.get_sprite_url") as mock_get_sprite_url:
            mock_get_sprite_url.return_value = "/artwork/1027"
            pl.add_pokemon_to_list(form_pokemon["name"], form_pokemon)

    # Artwork URL must be built with species id so the client requests /artwork/1027
    mock_get_sprite_url.assert_called_once_with(1027, is_artwork=True)

    # Prefetch must use species id so upstream returns 200, not 404
    mock_get_sprite.assert_called_once_with(
        "pokemon", 1027, other=True, official_artwork=True
    )

    # List entry should have the artwork URL (species-based) and original pokemon id
    assert len(pl.pokemon_list) == 1
    assert pl.pokemon_list[0]["id"] == 1026
    assert pl.pokemon_list[0]["official_artwork"] == "/artwork/1027"


def test_official_artwork_uses_pokemon_id_when_no_species_url():
    """
    When species url is missing (e.g. minimal payload), fall back to pokemon id.
    """
    pokemon = {
        "id": 25,
        "name": "pikachu",
        "sprites": {},
        "types": [],
    }
    pl = PokemonList({})
    pl.pokemon_list = []
    with patch("pokedex.lists.get_sprite") as mock_get_sprite:
        with patch("pokedex.lists.get_sprite_url") as mock_get_sprite_url:
            mock_get_sprite_url.return_value = "/artwork/25"
            pl.add_pokemon_to_list("pikachu", pokemon)

    mock_get_sprite_url.assert_called_once_with(25, is_artwork=True)
    mock_get_sprite.assert_called_once_with(
        "pokemon", 25, other=True, official_artwork=True
    )


def test_get_species_id_from_url():
    """Sanity check for the helper we rely on."""
    assert get_species_id_from_url(SPECIES_URL_1027) == 1027
    assert get_species_id_from_url("https://pokeapi.co/api/v2/pokemon-species/1/") == 1

"""
Unit tests for pokedex.loaders module.

Tests each loader function to ensure it delegates correctly to
APIResource.fetch_data with the right endpoint name and returns dicts.
"""

import pytest
from unittest.mock import patch, MagicMock
from pokedex import loaders
from pokedex.loaders import sprite


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pokemon_data():
    """Mock data for a Pokemon."""
    return {
        "name": "bulbasaur",
        "id": 1,
        "height": 7,
        "weight": 69,
        "base_experience": 64,
        "types": [{"type": {"name": "grass"}}],
    }


# ---------------------------------------------------------------------------
# All loaders should use fetch_data and return dicts
# ---------------------------------------------------------------------------

class TestLoadersFetchData:
    """Every loader should call APIResource.fetch_data with the correct
    endpoint and return a dict."""

    @pytest.mark.parametrize("loader_fn,endpoint,arg", [
        (loaders.pokemon_detail, "pokemon", "bulbasaur"),
        (loaders.berry, "berry", "cheri"),
        (loaders.berry_firmness, "berry-firmness", "very-soft"),
        (loaders.berry_flavor, "berry-flavor", "spicy"),
        (loaders.contest_type, "contest-type", "cool"),
        (loaders.contest_effect, "contest-effect", 1),
        (loaders.super_contest_effect, "super-contest-effect", 1),
        (loaders.encounter_method, "encounter-method", "walk"),
        (loaders.encounter_condition, "encounter-condition", "swarm"),
        (loaders.encounter_condition_value, "encounter-condition-value", "swarm-yes"),
        (loaders.evolution_chain, "evolution-chain", 1),
        (loaders.evolution_trigger, "evolution-trigger", "level-up"),
        (loaders.generation, "generation", "generation-i"),
        (loaders.pokedex, "pokedex", "national"),
        (loaders.version, "version", "red"),
        (loaders.version_group, "version-group", "red-blue"),
        (loaders.item, "item", "master-ball"),
        (loaders.item_attribute, "item-attribute", "countable"),
        (loaders.item_category, "item-category", "stat-boosts"),
        (loaders.item_fling_effect, "item-fling-effect", 1),
        (loaders.item_pocket, "item-pocket", "misc"),
        (loaders.machine, "machine", 1),
        (loaders.move, "move", "tackle"),
        (loaders.move_ailment, "move-ailment", "paralysis"),
        (loaders.move_battle_style, "move-battle-style", "attack"),
        (loaders.move_category, "move-category", "damage"),
        (loaders.move_damage_class, "move-damage-class", "physical"),
        (loaders.move_learn_method, "move-learn-method", "level-up"),
        (loaders.move_target, "move-target", "selected-pokemon"),
        (loaders.location, "location", 1),
        (loaders.location_area, "location-area", 1),
        (loaders.region, "region", "kanto"),
        # Previously buggy loaders -- now fixed:
        (loaders.ability, "ability", "stench"),
        (loaders.pal_park_area, "pal-park-area", "forest"),
        (loaders.characteristic, "characteristic", 1),
        (loaders.egg_group, "egg-group", "monster"),
        (loaders.gender, "gender", "female"),
        (loaders.growth_rate, "growth-rate", "slow"),
        (loaders.nature, "nature", "hardy"),
        (loaders.pokeathlon_stat, "pokeathlon-stat", "speed"),
        (loaders.pokemon, "pokemon", "bulbasaur"),
        (loaders.pokemon_color, "pokemon-color", "black"),
        (loaders.pokemon_form, "pokemon-form", "bulbasaur"),
        (loaders.pokemon_habitat, "pokemon-habitat", "cave"),
        (loaders.pokemon_shape, "pokemon-shape", "ball"),
        (loaders.pokemon_species, "pokemon-species", "bulbasaur"),
        (loaders.stat, "stat", "hp"),
        (loaders.type_, "type", "fire"),
        (loaders.language, "language", "en"),
    ])
    def test_loader_calls_fetch_data(self, loader_fn, endpoint, arg):
        """Each loader should call fetch_data with the correct endpoint."""
        expected = {"name": str(arg), "id": 1}
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = expected
            result = loader_fn(arg)

        mock_fetch.assert_called_once_with(endpoint, arg)
        assert isinstance(result, dict)
        assert result == expected


# ---------------------------------------------------------------------------
# Sprite loader
# ---------------------------------------------------------------------------

class TestSpriteLoader:
    def test_sprite_loader_creates_resource(self):
        """sprite() should create a SpriteResource and return it."""
        sprite_data = {"path": "sprites/pokemon/1.png", "img_data": b"binary"}

        with patch("pokedex.interface.SpriteResource._load") as mock_load:
            mock_load.return_value = None
            result = sprite("pokemon", 1)
            result.__dict__.update(sprite_data)

        assert result.path == sprite_data["path"]
        assert result.img_data == sprite_data["img_data"]
        mock_load.assert_called_once()

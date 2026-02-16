"""
Unit tests for pokedex.loaders module.

Tests each loader function to ensure it delegates correctly to
APIResource.fetch_data with the right endpoint name.

Known bugs documented here (will be fixed in Phase 1):
  - ability() uses endpoint "abilities" instead of "ability"
  - Several loaders use APIResource() constructor instead of fetch_data()
  - pokemon() has unreachable code after return
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
    """Mock data for a Pokémon."""
    return {
        "name": "bulbasaur",
        "id": 1,
        "height": 7,
        "weight": 69,
        "base_experience": 64,
        "types": [{"type": {"name": "grass"}}],
    }


# ---------------------------------------------------------------------------
# Loaders that use fetch_data correctly (return dicts)
# ---------------------------------------------------------------------------

class TestWorkingLoaders:
    """Loaders that correctly use APIResource.fetch_data and return dicts."""

    def test_pokemon_detail(self, mock_pokemon_data):
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = mock_pokemon_data
            result = loaders.pokemon_detail("bulbasaur")

        mock_fetch.assert_called_once_with("pokemon", "bulbasaur")
        assert result["name"] == "bulbasaur"
        assert result["id"] == 1

    def test_berry(self):
        berry_data = {"name": "cheri", "id": 1, "growth_time": 3}
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = berry_data
            result = loaders.berry("cheri")

        mock_fetch.assert_called_once_with("berry", "cheri")
        assert result["name"] == "cheri"

    def test_move(self):
        move_data = {"name": "tackle", "id": 1, "power": 40}
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = move_data
            result = loaders.move("tackle")

        mock_fetch.assert_called_once_with("move", "tackle")
        assert result["name"] == "tackle"

    def test_item(self):
        item_data = {"name": "master-ball", "id": 1}
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = item_data
            result = loaders.item("master-ball")

        mock_fetch.assert_called_once_with("item", "master-ball")
        assert result["name"] == "master-ball"

    def test_region(self):
        region_data = {"name": "kanto", "id": 1}
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = region_data
            result = loaders.region("kanto")

        mock_fetch.assert_called_once_with("region", "kanto")
        assert result["name"] == "kanto"

    def test_evolution_chain(self):
        chain_data = {"id": 1, "chain": {"species": {"name": "bulbasaur"}}}
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = chain_data
            result = loaders.evolution_chain(1)

        mock_fetch.assert_called_once_with("evolution-chain", 1)
        assert result["id"] == 1

    def test_generation(self):
        gen_data = {"name": "generation-i", "id": 1}
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = gen_data
            result = loaders.generation("generation-i")

        mock_fetch.assert_called_once_with("generation", "generation-i")

    def test_pokedex(self):
        dex_data = {"name": "national", "id": 1}
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = dex_data
            result = loaders.pokedex("national")

        mock_fetch.assert_called_once_with("pokedex", "national")

    def test_version(self):
        ver_data = {"name": "red", "id": 1}
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = ver_data
            result = loaders.version("red")

        mock_fetch.assert_called_once_with("version", "red")


# ---------------------------------------------------------------------------
# Known bug: ability() uses wrong endpoint name
# ---------------------------------------------------------------------------

class TestAbilityBug:
    """Documents the known bug where ability() uses 'abilities' instead of 'ability'."""

    def test_ability_uses_wrong_endpoint(self):
        """BUG: ability() passes 'abilities' to fetch_data, not 'ability'.

        This test documents the current (broken) behavior. When we fix this
        in Phase 1b, this test should be updated to assert 'ability' instead.
        """
        with patch("pokedex.interface.APIResource.fetch_data") as mock_fetch:
            mock_fetch.return_value = {"name": "stench", "id": 1}
            loaders.ability("stench")

        # Current (incorrect) behavior -- uses "abilities" not "ability"
        mock_fetch.assert_called_once_with("abilities", "stench")


# ---------------------------------------------------------------------------
# Known bug: loaders that return APIResource objects instead of dicts
# ---------------------------------------------------------------------------

class TestConstructorBug:
    """Documents loaders that use APIResource() constructor instead of fetch_data().

    These return APIResource objects (with lazy loading and attribute access)
    instead of plain dicts. This is inconsistent with the rest of the loaders
    and with how routes expect to use the results.

    When fixed in Phase 1b, these tests should be updated to verify
    they return dicts via fetch_data() instead.
    """

    def test_pokemon_loader_returns_object_not_dict(self):
        """BUG: pokemon() uses APIResource() constructor, returns an object."""
        with patch("pokedex.interface.APIResource.__init__", return_value=None) as mock_init:
            with patch("pokedex.interface.name_id_convert", return_value=("bulbasaur", 1)):
                result = loaders.pokemon("bulbasaur")

        # It calls the constructor, not fetch_data
        assert not isinstance(result, dict)

    def test_pal_park_area_returns_object(self):
        """BUG: pal_park_area() uses APIResource() constructor."""
        with patch("pokedex.interface.APIResource.__init__", return_value=None):
            with patch("pokedex.interface.name_id_convert", return_value=("forest", 1)):
                result = loaders.pal_park_area("forest")
        assert not isinstance(result, dict)


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

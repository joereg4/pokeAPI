"""
Unit tests for pokedex.common module.

Tests URL building, validation, species ID extraction,
and evolution chain traversal.
"""

import pytest
from pokedex.common import (
    api_url_build,
    cache_uri_build,
    sprite_url_build,
    sprite_filepath_build,
    validate,
    get_species_id_from_url,
    get_chain,
)
from conftest import load_mock_data


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

class TestValidate:
    def test_accepts_known_endpoint(self):
        """Known endpoints like 'pokemon' should not raise."""
        assert validate("pokemon") is None

    def test_rejects_unknown_endpoint(self):
        with pytest.raises(ValueError, match="Unknown API endpoint"):
            validate("not-a-real-endpoint")

    def test_rejects_non_int_resource_id(self):
        with pytest.raises(ValueError, match="Bad id"):
            validate("pokemon", "abc")

    def test_accepts_int_resource_id(self):
        assert validate("pokemon", 25) is None

    def test_accepts_none_resource_id(self):
        """None is valid -- means we want the endpoint list."""
        assert validate("pokemon", None) is None


# ---------------------------------------------------------------------------
# api_url_build
# ---------------------------------------------------------------------------

class TestApiUrlBuild:
    def test_endpoint_only(self):
        url = api_url_build("pokemon")
        assert url.endswith("/pokemon/")
        assert "pokeapi.co" in url

    def test_endpoint_with_id(self):
        url = api_url_build("pokemon", 25)
        assert url.endswith("/pokemon/25/")

    def test_endpoint_with_id_and_subresource(self):
        url = api_url_build("pokemon", 25, "encounters")
        assert url.endswith("/pokemon/25/encounters/")

    def test_rejects_invalid_endpoint(self):
        with pytest.raises(ValueError):
            api_url_build("fake-endpoint")


# ---------------------------------------------------------------------------
# cache_uri_build
# ---------------------------------------------------------------------------

class TestCacheUriBuild:
    def test_endpoint_only(self):
        uri = cache_uri_build("pokemon")
        assert uri == "pokemon/"

    def test_endpoint_with_id(self):
        uri = cache_uri_build("pokemon", 25)
        assert uri == "pokemon/25/"

    def test_endpoint_with_id_and_subresource(self):
        uri = cache_uri_build("pokemon", 25, "encounters")
        assert uri == "pokemon/25/encounters/"


# ---------------------------------------------------------------------------
# sprite_url_build
# ---------------------------------------------------------------------------

class TestSpriteUrlBuild:
    def test_default_sprite(self):
        """Default front sprite for pokemon 25."""
        url = sprite_url_build("pokemon", 25)
        assert "25.png" in url
        assert "/pokemon/" in url

    def test_official_artwork(self):
        url = sprite_url_build("pokemon", 25, other=True, official_artwork=True)
        assert "other/official-artwork/25.png" in url

    def test_shiny_back_female(self):
        url = sprite_url_build("pokemon", 25, back=True, shiny=True, female=True)
        assert "back" in url
        assert "shiny" in url
        assert "female" in url

    def test_dream_world(self):
        url = sprite_url_build("pokemon", 25, other=True, dream_world=True)
        assert "other/dream-world/25.png" in url


# ---------------------------------------------------------------------------
# sprite_filepath_build
# ---------------------------------------------------------------------------

class TestSpriteFilepathBuild:
    def test_default_filepath(self):
        path = sprite_filepath_build("pokemon", 25)
        assert path.endswith("25.png")
        assert "pokemon" in path

    def test_artwork_filepath(self):
        path = sprite_filepath_build("pokemon", 25, other=True, official_artwork=True)
        assert "other" in path
        assert "official-artwork" in path
        assert path.endswith("25.png")


# ---------------------------------------------------------------------------
# get_species_id_from_url
# ---------------------------------------------------------------------------

class TestGetSpeciesIdFromUrl:
    def test_standard_species_url(self):
        assert get_species_id_from_url("https://pokeapi.co/api/v2/pokemon-species/1/") == 1

    def test_high_id(self):
        assert get_species_id_from_url("https://pokeapi.co/api/v2/pokemon-species/1027/") == 1027

    def test_url_without_trailing_slash(self):
        assert get_species_id_from_url("https://pokeapi.co/api/v2/pokemon-species/25") == 25


# ---------------------------------------------------------------------------
# get_chain
# ---------------------------------------------------------------------------

class TestGetChain:
    def test_full_chain_from_base(self):
        """Load the bulbasaur evolution chain and verify traversal from the base species."""
        chain_data = load_mock_data("bulbasaur_evolution_chain.json")
        result = get_chain(chain_data, "bulbasaur")

        names = [entry["name"] for entry in result]
        assert names[0] == "bulbasaur"
        assert "ivysaur" in names
        assert "venusaur" in names

    def test_each_entry_has_species_id(self):
        """Every entry in the chain should have a species_id."""
        chain_data = load_mock_data("bulbasaur_evolution_chain.json")
        result = get_chain(chain_data, "bulbasaur")

        for entry in result:
            assert "species_id" in entry
            assert isinstance(entry["species_id"], int)

    def test_each_entry_has_sprite(self):
        """Every entry should have a sprite URL."""
        chain_data = load_mock_data("bulbasaur_evolution_chain.json")
        result = get_chain(chain_data, "bulbasaur")

        for entry in result:
            assert "sprite" in entry
            assert ".png" in entry["sprite"]

    def test_nonexistent_species_raises(self):
        """Requesting a species not in the chain should raise ValueError."""
        chain_data = load_mock_data("bulbasaur_evolution_chain.json")

        with pytest.raises(ValueError, match="not found in the evolution chain"):
            get_chain(chain_data, "pikachu")

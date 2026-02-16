"""
Tests for pokedex.lists module.

Verifies that:
  - Official artwork uses species ID (not form ID) to avoid 404s
  - PokemonList handles different data shapes correctly
  - Edge cases (empty data, missing keys) are handled gracefully
"""

import pytest
from unittest.mock import patch, MagicMock
from pokedex.lists import PokemonList, get_species_id_from_url


# ---------------------------------------------------------------------------
# Species URL constants
# ---------------------------------------------------------------------------

SPECIES_URL_1 = "https://pokeapi.co/api/v2/pokemon-species/1/"
SPECIES_URL_25 = "https://pokeapi.co/api/v2/pokemon-species/25/"
SPECIES_URL_1027 = "https://pokeapi.co/api/v2/pokemon-species/1027/"


# ---------------------------------------------------------------------------
# get_species_id_from_url
# ---------------------------------------------------------------------------

class TestGetSpeciesIdFromUrl:
    def test_standard_url(self):
        assert get_species_id_from_url(SPECIES_URL_1) == 1

    def test_high_id(self):
        assert get_species_id_from_url(SPECIES_URL_1027) == 1027

    def test_url_without_trailing_slash(self):
        assert get_species_id_from_url("https://pokeapi.co/api/v2/pokemon-species/25") == 25


# ---------------------------------------------------------------------------
# Official artwork uses species ID (issue #38)
# ---------------------------------------------------------------------------

class TestArtworkSpeciesId:
    """Artwork must use species ID for forms so upstream doesn't 404."""

    def test_form_pokemon_uses_species_id(self):
        """Form Pokemon (pokemon id != species id) should use species id for artwork."""
        form_pokemon = {
            "id": 1026,
            "name": "koraidon-limited-build",
            "species": {"name": "koraidon", "url": SPECIES_URL_1027},
            "sprites": {"other": {"official-artwork": {"front_default": None}}},
            "types": [],
        }
        pl = PokemonList({})
        pl.pokemon_list = []

        with patch("pokedex.lists.get_sprite") as mock_get_sprite, \
             patch("pokedex.lists.get_sprite_url") as mock_get_sprite_url:
            mock_get_sprite_url.return_value = "/artwork/1027"
            pl.add_pokemon_to_list(form_pokemon["name"], form_pokemon)

        mock_get_sprite_url.assert_called_once_with(1027, is_artwork=True)
        mock_get_sprite.assert_called_once_with("pokemon", 1027, other=True, official_artwork=True)
        assert pl.pokemon_list[0]["id"] == 1026
        assert pl.pokemon_list[0]["official_artwork"] == "/artwork/1027"

    def test_standard_pokemon_uses_own_id_as_species(self):
        """Standard Pokemon where id == species id should still work fine."""
        pokemon = {
            "id": 25,
            "name": "pikachu",
            "species": {"name": "pikachu", "url": SPECIES_URL_25},
            "sprites": {"front_default": "some_url"},
            "types": [{"type": {"name": "electric"}}],
        }
        pl = PokemonList({})
        pl.pokemon_list = []

        with patch("pokedex.lists.get_sprite") as mock_get_sprite, \
             patch("pokedex.lists.get_sprite_url") as mock_get_sprite_url:
            mock_get_sprite_url.return_value = "/artwork/25"
            pl.add_pokemon_to_list("pikachu", pokemon)

        mock_get_sprite_url.assert_called_once_with(25, is_artwork=True)
        assert pl.pokemon_list[0]["id"] == 25

    def test_missing_species_falls_back_to_pokemon_id(self):
        """When species URL is missing, fall back to pokemon ID."""
        pokemon = {
            "id": 25,
            "name": "pikachu",
            "sprites": {},
            "types": [],
        }
        pl = PokemonList({})
        pl.pokemon_list = []

        with patch("pokedex.lists.get_sprite") as mock_get_sprite, \
             patch("pokedex.lists.get_sprite_url") as mock_get_sprite_url:
            mock_get_sprite_url.return_value = "/artwork/25"
            pl.add_pokemon_to_list("pikachu", pokemon)

        mock_get_sprite_url.assert_called_once_with(25, is_artwork=True)


# ---------------------------------------------------------------------------
# PokemonList.identify_key
# ---------------------------------------------------------------------------

class TestIdentifyKey:
    """Tests for the key identification logic."""

    def test_identifies_pokemon_key(self):
        pl = PokemonList({"pokemon": [{"name": "bulbasaur"}]})
        pl.identify_key()
        assert pl.key == "pokemon"

    def test_identifies_pokemon_species_key(self):
        pl = PokemonList({"pokemon_species": [{"name": "bulbasaur"}]})
        pl.identify_key()
        assert pl.key == "pokemon_species"

    def test_identifies_pokemon_entries_key(self):
        data = {
            "pokemon_entries": [
                {"pokemon_species": {"name": "bulbasaur"}, "entry_number": 1}
            ]
        }
        pl = PokemonList(data)
        pl.identify_key()
        assert pl.key == "pokemon_entries"
        assert pl.pokemon_entries == [{"name": "bulbasaur"}]

    def test_identifies_varieties_key(self):
        pl = PokemonList({"varieties": [{"pokemon": {"name": "bulbasaur"}}]})
        pl.identify_key()
        assert pl.key == "varieties"

    def test_raises_on_unknown_data(self):
        pl = PokemonList({"unknown_key": []})
        with pytest.raises(ValueError, match="No valid key found"):
            pl.identify_key()


# ---------------------------------------------------------------------------
# PokemonList.create_pokemon_list
# ---------------------------------------------------------------------------

class TestCreatePokemonList:
    """Tests for the main list creation method."""

    def test_empty_data_returns_empty_list(self):
        """An empty data structure should produce an empty list."""
        pl = PokemonList({"pokemon": []})
        result = pl.create_pokemon_list()
        assert result == []

    def test_list_input_is_treated_as_entries(self):
        """When data is a list, it should be used directly as entries."""
        mock_pokemon = {
            "id": 1,
            "name": "bulbasaur",
            "sprites": {"front_default": "url"},
            "species": {"name": "bulbasaur", "url": SPECIES_URL_1},
            "types": [],
        }

        with patch("pokedex.lists.APIResource") as MockAR, \
             patch("pokedex.lists.get_sprite"), \
             patch("pokedex.lists.get_sprite_url", return_value="/artwork/1"):
            MockAR.fetch_data.return_value = mock_pokemon
            pl = PokemonList([{"name": "bulbasaur"}])
            result = pl.create_pokemon_list()

        assert len(result) == 1
        assert result[0]["name"] == "bulbasaur"

    def test_invalid_key_returns_empty_list(self):
        """Data with no recognized key should return empty list (after logging error)."""
        pl = PokemonList({"not_a_key": []})
        result = pl.create_pokemon_list()
        assert result == []

    def test_pokemon_without_sprites_is_skipped(self):
        """Pokemon entries without 'sprites' key should be skipped."""
        mock_pokemon = {"id": 1, "name": "missingno", "types": []}

        with patch("pokedex.lists.APIResource") as MockAR:
            MockAR.fetch_data.return_value = mock_pokemon
            pl = PokemonList({"pokemon": [{"name": "missingno"}]})
            result = pl.create_pokemon_list()

        assert result == []

    def test_result_is_sorted_by_id(self):
        """Output list should be sorted by Pokemon ID."""
        pokemon_3 = {
            "id": 3, "name": "venusaur",
            "sprites": {"front_default": "url"},
            "species": {"name": "venusaur", "url": "https://pokeapi.co/api/v2/pokemon-species/3/"},
            "types": [],
        }
        pokemon_1 = {
            "id": 1, "name": "bulbasaur",
            "sprites": {"front_default": "url"},
            "species": {"name": "bulbasaur", "url": SPECIES_URL_1},
            "types": [],
        }

        def fake_fetch(endpoint, name):
            return {"bulbasaur": pokemon_1, "venusaur": pokemon_3}[name]

        with patch("pokedex.lists.APIResource") as MockAR, \
             patch("pokedex.lists.get_sprite"), \
             patch("pokedex.lists.get_sprite_url", return_value="/artwork/1"):
            MockAR.fetch_data.side_effect = fake_fetch
            pl = PokemonList({"pokemon": [{"name": "venusaur"}, {"name": "bulbasaur"}]})
            result = pl.create_pokemon_list()

        assert result[0]["id"] < result[1]["id"]

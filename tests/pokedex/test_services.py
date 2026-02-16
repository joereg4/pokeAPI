# tests/pokedex/test_services.py
"""Unit tests for pokedex.services -- the unified Pokemon list builder.

Verifies:
  - Flexible input handling (list, dict with various keys)
  - Species ID artwork resolution (form Pokemon use species ID)
  - Variety fallback (species name -> default variety)
  - Serialization of all output entries
  - Sorting by Pokemon ID
  - build_species_variety_list expands species to varieties
"""

import pytest
from unittest.mock import patch, MagicMock
from pokedex.services import (
    build_pokemon_list,
    build_species_variety_list,
    _extract_entries,
    _extract_pokemon_name,
    _resolve_artwork_id,
    _fetch_with_variety_fallback,
    _get_entry_number,
)


# ---------------------------------------------------------------------------
# Constants for mock data
# ---------------------------------------------------------------------------

SPECIES_URL_25 = "https://pokeapi.co/api/v2/pokemon-species/25/"
SPECIES_URL_3 = "https://pokeapi.co/api/v2/pokemon-species/3/"

MOCK_PIKACHU = {
    "id": 25,
    "name": "pikachu",
    "species": {"name": "pikachu", "url": SPECIES_URL_25},
    "sprites": {"front_default": "https://example.com/25.png"},
    "types": [{"slot": 1, "type": {"name": "electric"}}],
}

MOCK_VENUSAUR = {
    "id": 3,
    "name": "venusaur",
    "species": {"name": "venusaur", "url": SPECIES_URL_3},
    "sprites": {"front_default": "https://example.com/3.png"},
    "types": [{"slot": 1, "type": {"name": "grass"}}],
}


# ---------------------------------------------------------------------------
# _extract_entries
# ---------------------------------------------------------------------------


class TestExtractEntries:
    """Tests for _extract_entries helper."""

    def test_list_input_returned_as_is(self):
        entries = [{"name": "pikachu"}]
        assert _extract_entries(entries) == entries

    def test_dict_with_results_key(self):
        data = {"results": [{"name": "pikachu"}], "count": 1}
        assert _extract_entries(data) == [{"name": "pikachu"}]

    def test_dict_with_pokemon_key(self):
        data = {"pokemon": [{"pokemon": {"name": "pikachu"}}]}
        assert _extract_entries(data) == [{"pokemon": {"name": "pikachu"}}]

    def test_dict_with_pokemon_species_key(self):
        data = {"pokemon_species": [{"name": "pikachu"}]}
        assert _extract_entries(data) == [{"name": "pikachu"}]

    def test_dict_with_pokemon_entries_key(self):
        data = {
            "pokemon_entries": [
                {"pokemon_species": {"name": "bulbasaur"}, "entry_number": 1}
            ]
        }
        result = _extract_entries(data)
        assert result == [{"name": "bulbasaur"}]

    def test_dict_with_held_by_pokemon_key(self):
        data = {"held_by_pokemon": [{"pokemon": {"name": "pikachu"}}]}
        assert _extract_entries(data) == [{"pokemon": {"name": "pikachu"}}]

    def test_dict_with_varieties_key(self):
        data = {"varieties": [{"pokemon": {"name": "venusaur-mega"}}]}
        assert _extract_entries(data) == [{"pokemon": {"name": "venusaur-mega"}}]

    def test_none_returns_empty(self):
        assert _extract_entries(None) == []

    def test_unknown_dict_returns_empty(self):
        assert _extract_entries({"not_a_key": []}) == []

    def test_empty_list_returns_empty(self):
        assert _extract_entries([]) == []


# ---------------------------------------------------------------------------
# _extract_pokemon_name
# ---------------------------------------------------------------------------


class TestExtractPokemonName:
    """Tests for _extract_pokemon_name helper."""

    def test_name_key(self):
        assert _extract_pokemon_name({"name": "pikachu"}) == "pikachu"

    def test_nested_pokemon_name(self):
        assert _extract_pokemon_name({"pokemon": {"name": "pikachu"}}) == "pikachu"

    def test_non_dict_returns_none(self):
        assert _extract_pokemon_name("not_a_dict") is None

    def test_empty_dict_returns_none(self):
        assert _extract_pokemon_name({}) is None

    def test_pokemon_key_not_dict_returns_none(self):
        assert _extract_pokemon_name({"pokemon": "not_a_dict"}) is None


# ---------------------------------------------------------------------------
# _resolve_artwork_id
# ---------------------------------------------------------------------------


class TestResolveArtworkId:
    """Tests for species ID artwork resolution."""

    def test_uses_species_id_from_url(self):
        pokemon = {
            "id": 10001,
            "species": {"url": "https://pokeapi.co/api/v2/pokemon-species/25/"},
        }
        assert _resolve_artwork_id(pokemon) == 25

    def test_falls_back_to_pokemon_id_when_no_species(self):
        pokemon = {"id": 42}
        assert _resolve_artwork_id(pokemon) == 42

    def test_falls_back_to_pokemon_id_when_species_none(self):
        pokemon = {"id": 42, "species": None}
        assert _resolve_artwork_id(pokemon) == 42

    def test_falls_back_when_species_url_missing(self):
        pokemon = {"id": 42, "species": {"name": "pikachu"}}
        assert _resolve_artwork_id(pokemon) == 42


# ---------------------------------------------------------------------------
# _get_entry_number
# ---------------------------------------------------------------------------


class TestGetEntryNumber:
    """Tests for extracting entry number from species data."""

    def test_extracts_first_entry_number(self):
        species = {
            "pokedex_numbers": [
                {"entry_number": 25, "pokedex": {"name": "national"}},
                {"entry_number": 22, "pokedex": {"name": "kanto"}},
            ]
        }
        assert _get_entry_number(species) == 25

    def test_returns_none_when_no_pokedex_numbers(self):
        assert _get_entry_number({}) is None

    def test_returns_none_when_empty_list(self):
        assert _get_entry_number({"pokedex_numbers": []}) is None


# ---------------------------------------------------------------------------
# _fetch_with_variety_fallback
# ---------------------------------------------------------------------------


class TestFetchWithVarietyFallback:
    """Tests for Pokemon fetching with variety fallback."""

    def test_returns_pokemon_on_success(self):
        with patch("pokedex.services.APIResource") as MockAR:
            MockAR.fetch_data.return_value = MOCK_PIKACHU
            result = _fetch_with_variety_fallback("pikachu")
        assert result["name"] == "pikachu"

    def test_tries_variety_on_value_error(self):
        variety_pokemon = {
            "id": 100,
            "name": "wormadam-plant",
            "species": {"name": "wormadam", "url": "..."},
            "sprites": {},
            "types": [],
        }
        species_data = {
            "varieties": [
                {"is_default": True, "pokemon": {"name": "wormadam-plant"}}
            ]
        }
        with patch("pokedex.services.APIResource") as MockAR:
            MockAR.fetch_data.side_effect = [
                ValueError("not found"),  # First call for "wormadam"
                species_data,              # Species lookup
                variety_pokemon,           # Variety pokemon lookup
            ]
            result = _fetch_with_variety_fallback("wormadam")

        assert result["name"] == "wormadam-plant"

    def test_returns_none_when_all_fail(self):
        with patch("pokedex.services.APIResource") as MockAR:
            MockAR.fetch_data.side_effect = ValueError("not found")
            result = _fetch_with_variety_fallback("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# build_pokemon_list
# ---------------------------------------------------------------------------


class TestBuildPokemonList:
    """Tests for the main build_pokemon_list function."""

    def _setup_mock(self, MockAR, pokemon_map):
        """Set up APIResource mock to return pokemon by name."""
        def fake_fetch(endpoint, name):
            if endpoint == "pokemon":
                if name in pokemon_map:
                    return pokemon_map[name]
                raise ValueError(f"{name} not found")
            return {}
        MockAR.fetch_data.side_effect = fake_fetch

    def test_list_input(self):
        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url", return_value="/artwork/25"):
            self._setup_mock(MockAR, {"pikachu": MOCK_PIKACHU})
            result = build_pokemon_list([{"name": "pikachu"}])

        assert len(result) == 1
        assert result[0]["name"] == "pikachu"
        assert result[0]["id"] == 25
        assert result[0]["official_artwork"] == "/artwork/25"

    def test_dict_with_results_key(self):
        data = {"results": [{"name": "pikachu"}], "count": 1}
        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url", return_value="/artwork/25"):
            self._setup_mock(MockAR, {"pikachu": MOCK_PIKACHU})
            result = build_pokemon_list(data)

        assert len(result) == 1
        assert result[0]["name"] == "pikachu"

    def test_nested_pokemon_name_format(self):
        """Handles entries like {"pokemon": {"name": "pikachu"}}."""
        data = [{"pokemon": {"name": "pikachu"}}]
        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url", return_value="/artwork/25"):
            self._setup_mock(MockAR, {"pikachu": MOCK_PIKACHU})
            result = build_pokemon_list(data)

        assert len(result) == 1
        assert result[0]["name"] == "pikachu"

    def test_results_sorted_by_id(self):
        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url", return_value="/artwork/1"):
            self._setup_mock(MockAR, {
                "pikachu": MOCK_PIKACHU,
                "venusaur": MOCK_VENUSAUR,
            })
            result = build_pokemon_list([
                {"name": "pikachu"},
                {"name": "venusaur"},
            ])

        assert result[0]["id"] == 3    # venusaur first (lower id)
        assert result[1]["id"] == 25   # pikachu second

    def test_empty_input_returns_empty(self):
        assert build_pokemon_list([]) == []
        assert build_pokemon_list(None) == []
        assert build_pokemon_list({}) == []

    def test_not_found_entries_are_skipped(self):
        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url", return_value="/artwork/25"):
            # pikachu succeeds, "ghost" fails for both pokemon and species
            MockAR.fetch_data.side_effect = [
                MOCK_PIKACHU,                  # pikachu pokemon
                ValueError("not found"),       # ghost pokemon
                ValueError("not found"),       # ghost species fallback
            ]
            result = build_pokemon_list([
                {"name": "pikachu"},
                {"name": "ghost"},
            ])

        assert len(result) == 1
        assert result[0]["name"] == "pikachu"

    def test_output_entries_are_serialized(self):
        """Every entry should have guaranteed template fields."""
        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url", return_value="/artwork/25"):
            self._setup_mock(MockAR, {"pikachu": MOCK_PIKACHU})
            result = build_pokemon_list([{"name": "pikachu"}])

        entry = result[0]
        # These fields are guaranteed by serialize_pokemon_list_entry
        assert "name" in entry
        assert "types" in entry
        assert "official_artwork" in entry
        assert "id" in entry
        assert "is_variety" in entry
        assert "variety_name" in entry

    def test_uses_species_id_for_artwork(self):
        """Artwork URL should use species ID, not pokemon ID."""
        form_pokemon = {
            "id": 10001,
            "name": "pikachu-cosplay",
            "species": {"name": "pikachu", "url": SPECIES_URL_25},
            "sprites": {"front_default": "url"},
            "types": [],
        }
        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url") as mock_sprite:
            mock_sprite.return_value = "/artwork/25"
            self._setup_mock(MockAR, {"pikachu-cosplay": form_pokemon})
            result = build_pokemon_list([{"name": "pikachu-cosplay"}])

        # Should call get_sprite_url with species ID 25, not pokemon ID 10001
        mock_sprite.assert_called_with(25, is_artwork=True)

    def test_variety_flag_set_correctly(self):
        """When using variety data, is_variety and variety_name should be set."""
        variety_pokemon = {
            "id": 100,
            "name": "wormadam-plant",
            "species": {"name": "wormadam", "url": "https://pokeapi.co/api/v2/pokemon-species/413/"},
            "sprites": {"front_default": "url"},
            "types": [],
        }
        species_data = {
            "varieties": [
                {"is_default": True, "pokemon": {"name": "wormadam-plant"}}
            ]
        }
        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url", return_value="/artwork/413"):
            MockAR.fetch_data.side_effect = [
                ValueError("not found"),  # wormadam pokemon
                species_data,             # wormadam species
                variety_pokemon,          # wormadam-plant pokemon
            ]
            result = build_pokemon_list([{"name": "wormadam"}])

        assert len(result) == 1
        assert result[0]["is_variety"] is True
        assert result[0]["variety_name"] == "wormadam-plant"


# ---------------------------------------------------------------------------
# build_species_variety_list
# ---------------------------------------------------------------------------


class TestBuildSpeciesVarietyList:
    """Tests for the species-to-varieties expansion."""

    def test_expands_species_to_varieties(self):
        species_data = {
            "varieties": [
                {"is_default": True, "pokemon": {"name": "venusaur"}},
                {"is_default": False, "pokemon": {"name": "venusaur-mega"}},
            ],
            "pokedex_numbers": [{"entry_number": 3, "pokedex": {"name": "national"}}],
        }
        mega = {
            "id": 10002,
            "name": "venusaur-mega",
            "species": {"name": "venusaur", "url": SPECIES_URL_3},
            "sprites": {"front_default": "url"},
            "types": [],
        }

        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url", return_value="/artwork/3"):
            MockAR.fetch_data.side_effect = [
                species_data,    # venusaur species
                MOCK_VENUSAUR,   # venusaur pokemon
                mega,            # venusaur-mega pokemon
            ]
            result = build_species_variety_list(["venusaur"])

        assert len(result) == 2
        assert result[0]["name"] == "venusaur"
        assert result[1]["name"] == "venusaur-mega"
        # Both should have entry_number from species
        assert result[0]["entry_number"] == 3
        assert result[1]["entry_number"] == 3

    def test_empty_species_list(self):
        assert build_species_variety_list([]) == []

    def test_species_not_found_is_skipped(self):
        with patch("pokedex.services.APIResource") as MockAR:
            MockAR.fetch_data.side_effect = ValueError("not found")
            result = build_species_variety_list(["nonexistent"])
        assert result == []

    def test_output_is_sorted_by_id(self):
        species_data = {
            "varieties": [
                {"is_default": False, "pokemon": {"name": "pikachu-cosplay"}},
                {"is_default": True, "pokemon": {"name": "pikachu"}},
            ],
            "pokedex_numbers": [],
        }
        cosplay = {
            "id": 10080,
            "name": "pikachu-cosplay",
            "species": {"name": "pikachu", "url": SPECIES_URL_25},
            "sprites": {},
            "types": [],
        }

        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url", return_value="/artwork/25"):
            MockAR.fetch_data.side_effect = [
                species_data,  # pikachu species
                cosplay,       # pikachu-cosplay pokemon
                MOCK_PIKACHU,  # pikachu pokemon
            ]
            result = build_species_variety_list(["pikachu"])

        assert result[0]["id"] == 25      # pikachu first (lower id)
        assert result[1]["id"] == 10080   # cosplay second


# ---------------------------------------------------------------------------
# Backward compatibility: helper.create_pokemon_list
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    """Ensure helper.create_pokemon_list still works as a thin wrapper."""

    def test_helper_delegates_to_service(self):
        with patch("pokedex.services.APIResource") as MockAR, \
             patch("pokedex.services.get_sprite_url", return_value="/artwork/25"):
            MockAR.fetch_data.return_value = MOCK_PIKACHU
            from pokedex.helper import create_pokemon_list
            result = create_pokemon_list([{"name": "pikachu"}])

        assert len(result) == 1
        assert result[0]["name"] == "pikachu"

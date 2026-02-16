# tests/pokedex/test_serializers.py
"""Unit tests for pokedex.serializers.

Each test class covers one serializer function.  The tests verify:
  1. Full data passes through unchanged (no data loss).
  2. Missing required fields get safe defaults (no UndefinedError).
  3. None / empty / wrong-type inputs are handled gracefully.
  4. Nested structures like meta, species, damage_relations are sanitised.
"""

import pytest
from pokedex.serializers import (
    serialize_pokemon,
    serialize_pokemon_species,
    serialize_move,
    serialize_item,
    serialize_ability,
    serialize_pokemon_list_entry,
    serialize_pokemon_list,
    _safe_nested,
    _ensure_list,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestSafeNested:
    """Tests for the _safe_nested utility."""

    def test_traverses_nested_dicts(self):
        data = {"a": {"b": {"c": 42}}}
        assert _safe_nested(data, "a", "b", "c") == 42

    def test_returns_default_on_missing_key(self):
        data = {"a": {"b": 1}}
        assert _safe_nested(data, "a", "x", default="fallback") == "fallback"

    def test_returns_default_on_none_intermediate(self):
        data = {"a": None}
        assert _safe_nested(data, "a", "b") is None

    def test_returns_default_on_non_dict_intermediate(self):
        data = {"a": "string_not_dict"}
        assert _safe_nested(data, "a", "b", default="nope") == "nope"

    def test_empty_keys_returns_data_itself(self):
        data = {"a": 1}
        assert _safe_nested(data) == {"a": 1}


class TestEnsureList:
    """Tests for the _ensure_list utility."""

    def test_returns_existing_list(self):
        assert _ensure_list({"items": [1, 2, 3]}, "items") == [1, 2, 3]

    def test_returns_empty_for_missing_key(self):
        assert _ensure_list({}, "items") == []

    def test_returns_empty_for_non_list_value(self):
        assert _ensure_list({"items": "not_a_list"}, "items") == []

    def test_returns_empty_for_none_value(self):
        assert _ensure_list({"items": None}, "items") == []


# ---------------------------------------------------------------------------
# serialize_pokemon
# ---------------------------------------------------------------------------


class TestSerializePokemon:
    """Tests for serialize_pokemon."""

    @pytest.fixture
    def full_pokemon(self):
        """Realistic pokemon data with all required fields."""
        return {
            "id": 25,
            "name": "pikachu",
            "species": {
                "name": "pikachu",
                "url": "https://pokeapi.co/api/v2/pokemon-species/25/",
            },
            "stats": [
                {"stat": {"name": "hp"}, "base_stat": 35},
                {"stat": {"name": "attack"}, "base_stat": 55},
            ],
            "abilities": [
                {
                    "slot": 1,
                    "ability": {
                        "name": "static",
                        "url": "https://pokeapi.co/api/v2/ability/9/",
                    },
                },
            ],
            "sprites": {"front_default": "https://example.com/sprite.png"},
            "moves": [
                {
                    "move": {"name": "thunder-shock"},
                    "version_group_details": [],
                }
            ],
            "types": [{"slot": 1, "type": {"name": "electric"}}],
            "base_experience": 112,
            "height": 4,
            "weight": 60,
            "is_default": True,
            "order": 35,
            "held_items": [],
        }

    def test_full_data_preserved(self, full_pokemon):
        result = serialize_pokemon(full_pokemon)
        assert result["id"] == 25
        assert result["name"] == "pikachu"
        assert result["species"]["name"] == "pikachu"
        assert len(result["stats"]) == 2
        assert result["base_experience"] == 112

    def test_extra_keys_preserved(self, full_pokemon):
        """Keys not explicitly handled should pass through via **data."""
        full_pokemon["custom_field"] = "custom_value"
        result = serialize_pokemon(full_pokemon)
        assert result["custom_field"] == "custom_value"

    def test_empty_dict_gets_safe_defaults(self):
        result = serialize_pokemon({})
        assert result["name"] == "Unknown"
        assert result["id"] is None
        assert result["species"] == {"name": "unknown", "url": ""}
        assert result["stats"] == []
        assert result["abilities"] == []
        assert result["sprites"] == {}
        assert result["moves"] == []
        assert result["types"] == []
        assert result["held_items"] == []

    def test_none_input_returns_safe_defaults(self):
        result = serialize_pokemon(None)
        assert result["name"] == "Unknown"
        assert result["stats"] == []

    def test_species_none_gets_fallback(self):
        result = serialize_pokemon({"name": "test", "species": None})
        assert result["species"] == {"name": "unknown", "url": ""}

    def test_sprites_none_gets_empty_dict(self):
        result = serialize_pokemon({"name": "test", "sprites": None})
        assert result["sprites"] == {}

    def test_non_list_stats_becomes_empty(self):
        result = serialize_pokemon({"stats": "not_a_list"})
        assert result["stats"] == []


# ---------------------------------------------------------------------------
# serialize_pokemon_species
# ---------------------------------------------------------------------------


class TestSerializePokemonSpecies:
    """Tests for serialize_pokemon_species."""

    @pytest.fixture
    def full_species(self):
        return {
            "name": "pikachu",
            "base_happiness": 70,
            "capture_rate": 190,
            "color": {"name": "yellow"},
            "egg_groups": [{"name": "field", "url": "..."}],
            "gender_rate": 4,
            "has_gender_differences": True,
            "hatch_counter": 10,
            "habitat": {"name": "forest"},
            "is_baby": False,
            "is_legendary": False,
            "is_mythical": False,
            "shape": {"name": "quadruped"},
            "flavor_text_entries": [
                {"flavor_text": "A cute pokemon.", "version": {"name": "red"}}
            ],
            "pokedex_numbers": [
                {
                    "entry_number": 25,
                    "pokedex": {"name": "national", "url": "..."},
                }
            ],
            "evolution_chain": {
                "url": "https://pokeapi.co/api/v2/evolution-chain/10/"
            },
            "varieties": [
                {"is_default": True, "pokemon": {"name": "pikachu"}}
            ],
        }

    def test_none_input_returns_none(self):
        """When species_data is None (not fetched), serializer returns None."""
        assert serialize_pokemon_species(None) is None

    def test_empty_dict_returns_none(self):
        assert serialize_pokemon_species({}) is None

    def test_full_data_preserved(self, full_species):
        result = serialize_pokemon_species(full_species)
        assert result["base_happiness"] == 70
        assert result["color"]["name"] == "yellow"
        assert len(result["egg_groups"]) == 1

    def test_missing_color_gets_fallback(self):
        result = serialize_pokemon_species({"name": "test", "color": None})
        assert result["color"] == {"name": "unknown"}

    def test_missing_habitat_gets_fallback(self):
        result = serialize_pokemon_species({"name": "test", "habitat": None})
        assert result["habitat"] == {"name": "unknown"}

    def test_missing_shape_gets_fallback(self):
        result = serialize_pokemon_species({"name": "test", "shape": None})
        assert result["shape"] == {"name": "unknown"}

    def test_booleans_default_to_false(self):
        result = serialize_pokemon_species({"name": "test"})
        assert result["has_gender_differences"] is False
        assert result["is_baby"] is False
        assert result["is_legendary"] is False
        assert result["is_mythical"] is False


# ---------------------------------------------------------------------------
# serialize_move
# ---------------------------------------------------------------------------


class TestSerializeMove:
    """Tests for serialize_move."""

    @pytest.fixture
    def full_move(self):
        return {
            "name": "thunderbolt",
            "type": {"name": "electric"},
            "power": 90,
            "accuracy": 100,
            "pp": 15,
            "priority": 0,
            "damage_class": {"name": "special"},
            "generation": {"name": "generation-i"},
            "effect_entries": [
                {"effect": "Deals damage.", "language": {"name": "en"}}
            ],
            "flavor_text_entries": [
                {
                    "flavor_text": "A strong electric attack.",
                    "language": {"name": "en"},
                    "version_group": {"name": "red-blue"},
                }
            ],
            "meta": {
                "crit_rate": 0,
                "drain": 0,
                "healing": 0,
                "min_hits": None,
                "max_hits": None,
                "min_turns": None,
                "max_turns": None,
                "ailment": {"name": "paralysis"},
                "ailment_chance": 10,
                "flinch_chance": 0,
                "stat_chance": 0,
                "category": {"name": "damage", "url": "..."},
            },
        }

    def test_full_data_preserved(self, full_move):
        result = serialize_move(full_move)
        assert result["name"] == "thunderbolt"
        assert result["power"] == 90
        assert result["meta"]["ailment"]["name"] == "paralysis"

    def test_empty_dict_gets_safe_defaults(self):
        result = serialize_move({})
        assert result["name"] == "Unknown"
        assert result["type"] == {"name": "unknown"}
        assert result["pp"] == 0
        assert result["priority"] == 0
        assert result["damage_class"] == {"name": "unknown"}
        assert result["generation"] == {"name": "unknown"}
        assert result["effect_entries"] == []
        assert result["flavor_text_entries"] == []
        assert result["meta"] is None

    def test_none_input_returns_safe_defaults(self):
        result = serialize_move(None)
        assert result["name"] == "Unknown"

    def test_meta_none_stays_none(self):
        """When meta is None, serializer keeps it None (template checks)."""
        result = serialize_move({"meta": None})
        assert result["meta"] is None

    def test_meta_partial_gets_defaults(self):
        """When meta dict exists but has missing keys, they get defaults."""
        result = serialize_move({"meta": {"crit_rate": 5}})
        assert result["meta"]["crit_rate"] == 5
        assert result["meta"]["drain"] == 0
        assert result["meta"]["healing"] == 0
        assert result["meta"]["ailment"] == {"name": "none"}
        assert result["meta"]["flinch_chance"] == 0

    def test_meta_ailment_none_gets_fallback(self):
        result = serialize_move({"meta": {"ailment": None}})
        assert result["meta"]["ailment"] == {"name": "none"}


# ---------------------------------------------------------------------------
# serialize_item
# ---------------------------------------------------------------------------


class TestSerializeItem:
    """Tests for serialize_item."""

    @pytest.fixture
    def full_item(self):
        return {
            "name": "potion",
            "cost": 300,
            "attributes": [{"name": "usable-overworld"}],
            "sprites": {"default": "https://example.com/potion.png"},
            "category": {"name": "medicine", "url": "..."},
            "effect_entries": [
                {"effect": "Restores HP.", "language": {"name": "en"}}
            ],
            "fling_effect": None,
            "fling_power": None,
            "flavor_text_entries": [
                {
                    "text": "Restores 20 HP.",
                    "language": {"name": "en"},
                    "version_group": {"name": "red-blue"},
                }
            ],
            "game_indices": [
                {"generation": {"name": "generation-i"}, "game_index": 17}
            ],
        }

    def test_full_data_preserved(self, full_item):
        result = serialize_item(full_item)
        assert result["name"] == "potion"
        assert result["cost"] == 300
        assert result["sprites"]["default"] == "https://example.com/potion.png"

    def test_empty_dict_gets_safe_defaults(self):
        result = serialize_item({})
        assert result["name"] == "Unknown"
        assert result["cost"] == 0
        assert result["attributes"] == []
        assert result["sprites"] == {"default": None}
        assert result["effect_entries"] == []
        assert result["flavor_text_entries"] == []
        assert result["game_indices"] == []

    def test_none_input_returns_safe_defaults(self):
        result = serialize_item(None)
        assert result["name"] == "Unknown"

    def test_sprites_non_dict_gets_fallback(self):
        result = serialize_item({"sprites": "invalid"})
        assert result["sprites"] == {"default": None}

    def test_sprites_none_gets_fallback(self):
        result = serialize_item({"sprites": None})
        assert result["sprites"] == {"default": None}


# ---------------------------------------------------------------------------
# serialize_ability
# ---------------------------------------------------------------------------


class TestSerializeAbility:
    """Tests for serialize_ability."""

    @pytest.fixture
    def full_ability(self):
        return {
            "name": "static",
            "effect_entries": [
                {
                    "effect": "May paralyse on contact.",
                    "language": {"name": "en"},
                }
            ],
            "flavor_text_entries": [
                {
                    "flavor_text": "Contact may paralyse.",
                    "language": {"name": "en"},
                    "version_group": {"name": "red-blue"},
                }
            ],
            "pokemon": [{"pokemon": {"name": "pikachu"}}],
            "generation": {"name": "generation-iii"},
        }

    def test_full_data_preserved(self, full_ability):
        result = serialize_ability(full_ability)
        assert result["name"] == "static"
        assert len(result["effect_entries"]) == 1
        assert len(result["flavor_text_entries"]) == 1

    def test_empty_dict_gets_safe_defaults(self):
        result = serialize_ability({})
        assert result["name"] == "Unknown"
        assert result["effect_entries"] == []
        assert result["flavor_text_entries"] == []
        assert result["pokemon"] == []
        assert result["generation"] == {"name": "unknown"}

    def test_none_input_returns_safe_defaults(self):
        result = serialize_ability(None)
        assert result["name"] == "Unknown"

    def test_non_list_entries_become_empty(self):
        result = serialize_ability(
            {"effect_entries": "bad", "flavor_text_entries": 42}
        )
        assert result["effect_entries"] == []
        assert result["flavor_text_entries"] == []


# ---------------------------------------------------------------------------
# serialize_pokemon_list_entry / serialize_pokemon_list
# ---------------------------------------------------------------------------


class TestSerializePokemonListEntry:
    """Tests for serialize_pokemon_list_entry."""

    @pytest.fixture
    def full_entry(self):
        return {
            "name": "pikachu",
            "types": [{"slot": 1, "type": {"name": "electric"}}],
            "official_artwork": "https://example.com/25.png",
            "id": 25,
            "entry_number": 25,
            "is_variety": False,
            "variety_name": None,
        }

    def test_full_entry_preserved(self, full_entry):
        result = serialize_pokemon_list_entry(full_entry)
        assert result["name"] == "pikachu"
        assert result["id"] == 25
        assert len(result["types"]) == 1

    def test_empty_dict_gets_safe_defaults(self):
        result = serialize_pokemon_list_entry({})
        assert result["name"] == "Unknown"
        assert result["types"] == []
        assert result["official_artwork"] is None
        assert result["id"] is None
        assert result["is_variety"] is False

    def test_none_input_returns_safe_defaults(self):
        result = serialize_pokemon_list_entry(None)
        assert result["name"] == "Unknown"
        assert result["types"] == []

    def test_extra_keys_preserved(self):
        result = serialize_pokemon_list_entry(
            {"name": "test", "sprites": {"a": "b"}}
        )
        assert result["sprites"] == {"a": "b"}


class TestSerializePokemonList:
    """Tests for serialize_pokemon_list (batch serializer)."""

    def test_list_of_entries(self):
        entries = [{"name": "bulbasaur"}, {"name": "charmander"}]
        result = serialize_pokemon_list(entries)
        assert len(result) == 2
        assert result[0]["name"] == "bulbasaur"
        assert result[1]["name"] == "charmander"
        # Each entry should have guaranteed fields
        assert result[0]["types"] == []

    def test_empty_list(self):
        assert serialize_pokemon_list([]) == []

    def test_none_input(self):
        assert serialize_pokemon_list(None) == []

    def test_non_list_input(self):
        assert serialize_pokemon_list("not_a_list") == []

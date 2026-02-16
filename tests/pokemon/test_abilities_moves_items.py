"""
Tests for the abilities_moves_items blueprint routes.

All external API calls are mocked -- no real network requests.
Uses the shared mock_api and mock_requests fixtures from conftest.py.
"""

import pytest


# ---------------------------------------------------------------------------
# Fixtures: mock data for this module
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_mocks(mock_api, mock_requests):
    """Register mock responses for the endpoints tested in this module."""
    # Ability
    ability_data = {
        "name": "stench", "id": 1,
        "effect_entries": [{"effect": "Has a 10% chance of making the target flinch.", "language": {"name": "en"}}],
        "pokemon": [{"pokemon": {"name": "grimer", "url": "https://pokeapi.co/api/v2/pokemon/88/"}}],
        "flavor_text_entries": [],
        "names": [{"name": "Stench", "language": {"name": "en"}}],
        "generation": {"name": "generation-iii"},
    }
    mock_api.register("ability", 1, ability_data)
    mock_api.register("ability", "stench", ability_data)

    # Pokemon for ability's pokemon list
    mock_api.register("pokemon", "grimer", {
        "name": "grimer", "id": 88,
        "sprites": {"front_default": "url"},
        "species": {"name": "grimer", "url": "https://pokeapi.co/api/v2/pokemon-species/88/"},
        "types": [{"type": {"name": "poison"}}],
    })

    # Item -- template needs: name, effect_entries, cost, category.name,
    #   flavor_text_entries[].version_group.name, game_indices, fling_power, fling_effect
    item_data = {
        "name": "master-ball", "id": 1,
        "cost": 0,
        "fling_power": None,
        "fling_effect": None,
        "effect_entries": [{"effect": "Catches any wild Pokemon.", "short_effect": "Catches any wild Pokemon.", "language": {"name": "en"}}],
        "flavor_text_entries": [{"text": "The best ball.", "language": {"name": "en"}, "version_group": {"name": "red-blue", "url": "https://pokeapi.co/api/v2/version-group/1/"}}],
        "category": {"name": "standard-balls", "url": "https://pokeapi.co/api/v2/item-category/34/"},
        "held_by_pokemon": [],
        "game_indices": [],
        "names": [{"name": "Master Ball", "language": {"name": "en"}}],
        "sprites": {"default": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/master-ball.png"},
        "attributes": [],
        "baby_trigger_for": None,
    }
    mock_api.register("item", 1, item_data)
    mock_api.register("item", "master-ball", item_data)

    # Item attribute -- template needs: name, descriptions[].description, items[]
    mock_api.register("item-attribute", 1, {
        "name": "countable", "id": 1,
        "descriptions": [{"description": "Has a count in the bag.", "language": {"name": "en"}}],
        "items": [{"name": "master-ball", "url": "https://pokeapi.co/api/v2/item/1/"}],
    })

    # Item category
    mock_api.register("item-category", 1, {
        "name": "stat-boosts", "id": 1,
        "items": [{"name": "protein"}],
        "pocket": {"name": "medicine"},
    })

    # Move -- template needs: priority, contest_combos, contest_type, contest_effect,
    #   super_contest_effect, flavor_text_entries, machines, past_values, stat_changes, target
    move_data = {
        "name": "pound", "id": 1, "power": 40, "pp": 35, "accuracy": 100,
        "priority": 0,
        "type": {"name": "normal"},
        "damage_class": {"name": "physical"},
        "target": {"name": "selected-pokemon"},
        "meta": {
            "category": {"name": "damage", "url": "https://pokeapi.co/api/v2/move-category/0/"},
            "ailment": {"name": "none"}, "ailment_chance": 0, "crit_rate": 0,
            "drain": 0, "flinch_chance": 0, "healing": 0, "max_hits": None,
            "max_turns": None, "min_hits": None, "min_turns": None, "stat_chance": 0,
        },
        "effect_entries": [{"effect": "Does damage.", "short_effect": "Does damage.", "language": {"name": "en"}}],
        "flavor_text_entries": [{"flavor_text": "Pounds with forelegs or tail.", "language": {"name": "en"}, "version_group": {"name": "red-blue"}}],
        "learned_by_pokemon": [],
        "names": [{"name": "Pound", "language": {"name": "en"}}],
        "generation": {"name": "generation-i"},
        "machines": [],
        "past_values": [],
        "stat_changes": [],
        "contest_combos": None,
        "contest_type": None,
        "contest_effect": None,
        "super_contest_effect": None,
    }
    mock_api.register("move", 1, move_data)
    mock_api.register("move", "pound", move_data)

    # Move category
    mock_api.register("move-category", 1, {"name": "damage", "id": 1, "moves": []})
    mock_api.register("move-category", "damage", {"name": "damage", "id": 1, "moves": []})

    # Move damage class
    mock_api.register("move-damage-class", 1, {"name": "status", "id": 1})

    # Move learn method -- template needs: name, descriptions[], version_groups[]
    mock_api.register("move-learn-method", 1, {
        "name": "level-up", "id": 1,
        "descriptions": [{"description": "Learned when a Pokemon reaches a certain level.", "language": {"name": "en"}}],
        "version_groups": [{"name": "red-blue", "url": "https://pokeapi.co/api/v2/version-group/1/"}],
        "names": [{"name": "Level up", "language": {"name": "en"}}],
    })
    mock_api.register("move-learn-method", "level-up", mock_api.responses[("move-learn-method", "1")])

    # Machine -- template needs: id, item (full data), move (full data), version_group (full data)
    mock_api.register("machine", 1, {
        "id": 1,
        "item": {"name": "tm01", "url": "https://pokeapi.co/api/v2/item/305/"},
        "move": {"name": "mega-punch", "url": "https://pokeapi.co/api/v2/move/5/"},
        "version_group": {"name": "red-blue", "url": "https://pokeapi.co/api/v2/version-group/1/"},
    })
    # Machine detail fetches these separately
    mock_api.register("item", "tm01", {
        "name": "tm01", "id": 305,
        "cost": 3000,
        "category": {"name": "all-machines"},
        "effect_entries": [{"short_effect": "Teaches Mega Punch.", "language": {"name": "en"}}],
    })
    mock_api.register("move", "mega-punch", {
        "name": "mega-punch", "id": 5,
        "type": {"name": "normal"},
        "power": 80, "accuracy": 85, "pp": 20,
        "effect_entries": [{"short_effect": "Deals damage.", "language": {"name": "en"}}],
    })
    mock_api.register("version-group", "red-blue", {
        "name": "red-blue", "id": 1,
        "generation": {"name": "generation-i"},
        "versions": [{"name": "red"}, {"name": "blue"}],
    })

    # List endpoint (via mock_requests for fetch_all_results)
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "stench"}, {"name": "drizzle"}],
        "count": 2, "next": None,
    }


# ---------------------------------------------------------------------------
# Ability routes
# ---------------------------------------------------------------------------

class TestAbilityRoutes:
    def test_ability_list(self, client):
        response = client.get("/ability/")
        assert response.status_code == 200

    def test_ability_by_id(self, client):
        response = client.get("/ability/1")
        assert response.status_code == 200
        assert b"stench" in response.data.lower()

    def test_ability_by_name(self, client):
        response = client.get("/ability/stench")
        assert response.status_code == 200

    def test_ability_not_found(self, client):
        response = client.get("/ability/nonexistent")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Item routes
# ---------------------------------------------------------------------------

class TestItemRoutes:
    def test_item_by_id(self, client):
        response = client.get("/item/1")
        assert response.status_code == 200

    def test_item_by_name(self, client):
        response = client.get("/item/master-ball")
        assert response.status_code == 200

    def test_item_not_found(self, client):
        response = client.get("/item/nonexistent")
        assert response.status_code == 404

    def test_item_attribute_by_id(self, client):
        response = client.get("/item-attribute/1")
        assert response.status_code == 200

    def test_item_category_by_id(self, client):
        response = client.get("/item-category/1")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Move routes
# ---------------------------------------------------------------------------

class TestMoveRoutes:
    def test_move_by_id(self, client):
        response = client.get("/move/1")
        assert response.status_code == 200

    def test_move_by_name(self, client):
        response = client.get("/move/pound")
        assert response.status_code == 200

    def test_move_not_found(self, client):
        response = client.get("/move/nonexistent")
        assert response.status_code == 404

    def test_move_category_by_id(self, client):
        response = client.get("/move-category/1")
        assert response.status_code == 200

    def test_move_category_not_found(self, client):
        response = client.get("/move-category/nonexistent")
        assert response.status_code == 404

    def test_move_damage_class_by_id(self, client):
        response = client.get("/move-damage-class/1")
        assert response.status_code == 200

    def test_move_learn_method_by_id(self, client):
        response = client.get("/move-learn-method/1")
        assert response.status_code == 200

    def test_move_learn_method_list(self, client):
        response = client.get("/move-learn-method/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Machine routes
# ---------------------------------------------------------------------------

class TestMachineRoutes:
    def test_machine_by_id(self, client):
        response = client.get("/machine/1")
        assert response.status_code == 200

    def test_machine_not_found(self, client):
        response = client.get("/machine/9999")
        assert response.status_code in (400, 404, 500)

"""
Tests for the characteristics_stats blueprint routes.

All external API calls are mocked.

NOTE: nature has no dedicated route -- it would be served by the generic
handler in utilities.py, but the sprite route intercepts it. This is a
known bug tracked for Phase 1.
"""

import pytest


@pytest.fixture(autouse=True)
def setup_mocks(mock_api, mock_requests):
    """Register mock responses for characteristic and stat endpoints."""
    # Characteristic -- template needs: id, descriptions[].description,
    #   highest_stat.name, possible_values[]
    mock_api.register("characteristic", 1, {
        "id": 1,
        "gene_modulo": 0,
        "possible_values": [0, 5, 10, 15, 20, 25, 30],
        "highest_stat": {"name": "hp", "url": "https://pokeapi.co/api/v2/stat/1/"},
        "descriptions": [
            {"description": "Loves to eat", "language": {"name": "en", "url": "https://pokeapi.co/api/v2/language/9/"}}
        ],
    })

    # Stat -- template needs: name, game_index, is_battle_only,
    #   move_damage_class, affecting_natures, affecting_moves
    mock_api.register("stat", 1, {
        "name": "hp", "id": 1,
        "game_index": 1,
        "is_battle_only": False,
        "move_damage_class": None,
        "affecting_moves": {"increase": [], "decrease": []},
        "affecting_natures": {"increase": [], "decrease": []},
        "names": [{"name": "HP", "language": {"name": "en"}}],
        "characteristics": [],
    })
    mock_api.register("stat", "hp", mock_api.responses[("stat", "1")])

    # Characteristic list needs URL-based items for the list route
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [
            {"url": "https://pokeapi.co/api/v2/characteristic/1/"},
            {"url": "https://pokeapi.co/api/v2/characteristic/2/"},
        ],
        "count": 2, "next": None,
    }


class TestCharacteristicRoutes:
    def test_characteristic_list(self, client):
        response = client.get("/characteristic/")
        assert response.status_code == 200

    def test_characteristic_detail(self, client):
        response = client.get("/characteristic/1")
        assert response.status_code == 200

    def test_characteristic_not_found(self, client):
        response = client.get("/characteristic/99999")
        assert response.status_code in (400, 404)


class TestStatRoutes:
    """Stat has a dedicated route -- detail only, no list."""

    def test_stat_detail_by_id(self, client):
        response = client.get("/stat/1")
        assert response.status_code == 200

    def test_stat_detail_by_name(self, client):
        response = client.get("/stat/hp")
        assert response.status_code == 200

    def test_stat_not_found(self, client):
        response = client.get("/stat/nonexistent")
        assert response.status_code in (400, 404)


class TestSpriteRouteConflict:
    """Verify that nature URLs are intercepted by the sprite blueprint.
    Nature has no dedicated route.

    This documents a known bug -- see Phase 1 plan.
    """

    def test_nature_intercepted_by_sprite_route(self, client):
        response = client.get("/nature/1")
        assert response.status_code == 400

"""
Tests for evolution and breeding (egg group) routes.

All external API calls are mocked.

NOTE: evolution-chain and evolution-trigger have no dedicated routes.
They would normally be served by the generic `/<api_endpoint>/<id_or_name>`
handler in utilities.py, but the sprite route `/<pokemon_id>/<sprite_type>`
intercepts them first. This is a known bug (tracked for Phase 1).
"""

import pytest


@pytest.fixture(autouse=True)
def setup_mocks(mock_api, mock_requests):
    """Register mock responses for egg group endpoints."""
    # Egg group
    mock_api.register("egg-group", 1, {
        "name": "monster", "id": 1,
        "pokemon_species": [
            {"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon-species/1/"},
        ],
        "names": [{"name": "Monster", "language": {"name": "en"}}],
    })
    mock_api.register("egg-group", "monster", mock_api.responses[("egg-group", "1")])

    # Pokemon data needed for species lists
    mock_api.register("pokemon", "bulbasaur", {
        "name": "bulbasaur", "id": 1,
        "sprites": {"front_default": "url"},
        "species": {"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon-species/1/"},
        "types": [{"type": {"name": "grass"}}],
    })

    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "monster"}], "count": 1, "next": None,
    }


class TestEggGroupRoutes:
    def test_egg_group_list(self, client):
        response = client.get("/egg-group/")
        assert response.status_code == 200

    def test_egg_group_detail_by_id(self, client):
        response = client.get("/egg-group/1")
        assert response.status_code == 200

    def test_egg_group_detail_by_name(self, client):
        response = client.get("/egg-group/monster")
        assert response.status_code == 200

    def test_egg_group_not_found(self, client):
        response = client.get("/egg-group/nonexistent")
        assert response.status_code in (400, 404)


class TestSpriteRouteConflict:
    """Verify that evolution-chain and evolution-trigger URLs are
    intercepted by the sprite blueprint's catch-all pattern.
    These endpoints have no dedicated routes and cannot reach the
    generic handler in utilities.py.

    This documents a known bug -- see Phase 1 plan.
    """

    def test_evolution_chain_intercepted_by_sprite_route(self, client):
        """evolution-chain/<id> is captured by /<pokemon_id>/<sprite_type>."""
        response = client.get("/evolution-chain/1")
        # Returns 400 "Invalid sprite type" from the sprite blueprint
        assert response.status_code == 400

    def test_evolution_trigger_intercepted_by_sprite_route(self, client):
        """evolution-trigger/<name> is captured by /<pokemon_id>/<sprite_type>."""
        response = client.get("/evolution-trigger/level-up")
        assert response.status_code == 400

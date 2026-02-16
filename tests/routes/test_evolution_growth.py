"""
Tests for the evolution_growth blueprint routes.

All external API calls are mocked.

NOTE: growth-rate and gender have no dedicated routes. They would be
served by the generic handler in utilities.py, but the sprite route
`/<pokemon_id>/<sprite_type>` intercepts them. This is a known bug
tracked for Phase 1.
"""

import pytest


@pytest.fixture(autouse=True)
def setup_mocks(mock_api, mock_requests):
    """Register mock responses for generation endpoint."""
    # Generation -- template needs: name, main_region.name, abilities[],
    #   moves[], types[], version_groups[], pokemon_species[]
    mock_api.register("generation", 1, {
        "name": "generation-i", "id": 1,
        "main_region": {"name": "kanto", "url": "https://pokeapi.co/api/v2/region/1/"},
        "abilities": [{"name": "stench", "url": "https://pokeapi.co/api/v2/ability/1/"}],
        "moves": [{"name": "pound", "url": "https://pokeapi.co/api/v2/move/1/"}],
        "types": [{"name": "normal", "url": "https://pokeapi.co/api/v2/type/1/"}],
        "version_groups": [{"name": "red-blue", "url": "https://pokeapi.co/api/v2/version-group/1/"}],
        "pokemon_species": [{"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon-species/1/"}],
        "names": [{"name": "Generation I", "language": {"name": "en"}}],
    })
    mock_api.register("generation", "generation-i", mock_api.responses[("generation", "1")])

    # Pokemon data for species lists
    mock_api.register("pokemon", "bulbasaur", {
        "name": "bulbasaur", "id": 1,
        "sprites": {"front_default": "url"},
        "species": {"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon-species/1/"},
        "types": [{"type": {"name": "grass"}}],
    })

    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "generation-i"}], "count": 1, "next": None,
    }


class TestGenerationRoutes:
    def test_generation_list(self, client):
        response = client.get("/generation/")
        assert response.status_code == 200

    def test_generation_detail_by_id(self, client):
        response = client.get("/generation/1")
        assert response.status_code == 200

    def test_generation_detail_by_name(self, client):
        response = client.get("/generation/generation-i")
        assert response.status_code == 200

    def test_generation_not_found(self, client):
        response = client.get("/generation/nonexistent")
        assert response.status_code in (400, 404)


class TestSpriteRouteConflict:
    """Verify that growth-rate and gender URLs are intercepted by the
    sprite blueprint. These endpoints have no dedicated routes.

    This documents a known bug -- see Phase 1 plan.
    """

    def test_growth_rate_intercepted_by_sprite_route(self, client):
        response = client.get("/growth-rate/1")
        assert response.status_code == 400

    def test_gender_intercepted_by_sprite_route(self, client):
        response = client.get("/gender/1")
        assert response.status_code == 400

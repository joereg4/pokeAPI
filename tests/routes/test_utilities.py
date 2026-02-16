"""
Tests for the utilities blueprint routes (versions, version-groups).

All external API calls are mocked.

NOTE: language has no dedicated route -- it would be served by the generic
handler in utilities.py, but the sprite route intercepts it. This is a
known bug tracked for Phase 1.
"""

import pytest


@pytest.fixture(autouse=True)
def setup_mocks(mock_api, mock_requests):
    """Register mock responses for utility endpoints."""
    # Version -- template needs: name, version_group.name
    mock_api.register("version", 1, {
        "name": "red", "id": 1,
        "version_group": {"name": "red-blue", "url": "https://pokeapi.co/api/v2/version-group/1/"},
        "names": [{"name": "Red", "language": {"name": "en"}}],
    })
    mock_api.register("version", "red", mock_api.responses[("version", "1")])

    # Version group -- template needs: name, generation.name, regions[],
    #   pokedexes[], versions[], move_learn_methods[]
    mock_api.register("version-group", 1, {
        "name": "red-blue", "id": 1,
        "generation": {"name": "generation-i", "url": "https://pokeapi.co/api/v2/generation/1/"},
        "regions": [{"name": "kanto", "url": "https://pokeapi.co/api/v2/region/1/"}],
        "pokedexes": [{"name": "kanto", "url": "https://pokeapi.co/api/v2/pokedex/2/"}],
        "versions": [{"name": "red"}, {"name": "blue"}],
        "move_learn_methods": [{"name": "level-up"}],
    })
    mock_api.register("version-group", "red-blue", mock_api.responses[("version-group", "1")])


class TestVersionRoutes:
    """Version has a dedicated detail route."""

    def test_version_detail_by_id(self, client):
        response = client.get("/version/1")
        assert response.status_code == 200

    def test_version_detail_by_name(self, client):
        response = client.get("/version/red")
        assert response.status_code == 200

    def test_version_not_found(self, client):
        response = client.get("/version/nonexistent")
        assert response.status_code in (400, 404)


class TestVersionGroupRoutes:
    """Version group has a dedicated detail route."""

    def test_version_group_detail_by_id(self, client):
        response = client.get("/version-group/1")
        assert response.status_code == 200

    def test_version_group_detail_by_name(self, client):
        response = client.get("/version-group/red-blue")
        assert response.status_code == 200

    def test_version_group_not_found(self, client):
        response = client.get("/version-group/nonexistent")
        assert response.status_code in (400, 404)


class TestSpriteRouteConflict:
    """Verify that language URLs are intercepted by the sprite blueprint.
    Language has no dedicated route.

    This documents a known bug -- see Phase 1 plan.
    """

    def test_language_intercepted_by_sprite_route(self, client):
        response = client.get("/language/1")
        assert response.status_code == 400

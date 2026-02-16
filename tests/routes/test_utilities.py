"""
Tests for the utilities blueprint routes (languages, versions, etc.).

All external API calls are mocked.

language is served by the generic handler in utilities.py
(now reachable after sprite prefix fix).
"""

import pytest


@pytest.fixture(autouse=True)
def setup_mocks(mock_api, mock_requests):
    """Register mock responses for utility endpoints."""
    # Language -- served by generic route
    mock_api.register("language", 1, {
        "name": "ja-Hrkt", "id": 1,
        "official": True,
        "iso639": "ja",
        "iso3166": "jp",
        "names": [{"name": "Japanese", "language": {"name": "en"}}],
    })
    mock_api.register("language", "en", {
        "name": "en", "id": 9,
        "official": True,
        "iso639": "en",
        "iso3166": "us",
        "names": [{"name": "English", "language": {"name": "en"}}],
    })

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


class TestLanguageRoutes:
    """Language served by generic route."""

    def test_language_detail_by_id(self, client):
        response = client.get("/language/1")
        assert response.status_code == 200

    def test_language_detail_by_name(self, client):
        response = client.get("/language/en")
        assert response.status_code == 200

    def test_language_not_found(self, client):
        response = client.get("/language/nonexistent")
        assert response.status_code == 404


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
        assert response.status_code == 404


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
        assert response.status_code == 404

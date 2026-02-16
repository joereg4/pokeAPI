"""
Tests for location and region routes.

All external API calls are mocked.

NOTE: pal-park-area has no dedicated route -- it would be served by the
generic handler in utilities.py, but the sprite route intercepts it.
This is a known bug tracked for Phase 1.
"""

import pytest


@pytest.fixture(autouse=True)
def setup_mocks(mock_api, mock_requests):
    """Register mock responses for location and region endpoints."""
    # Location
    mock_api.register("location", 1, {
        "name": "canalave-city", "id": 1,
        "region": {"name": "sinnoh", "url": "https://pokeapi.co/api/v2/region/4/"},
        "areas": [{"name": "canalave-city-area", "url": "https://pokeapi.co/api/v2/location-area/1/"}],
        "names": [{"name": "Canalave City", "language": {"name": "en"}}],
    })
    mock_api.register("location", "canalave-city", mock_api.responses[("location", "1")])

    # Location area
    mock_api.register("location-area", 1, {
        "name": "canalave-city-area", "id": 1,
        "location": {"name": "canalave-city"},
        "pokemon_encounters": [
            {"pokemon": {"name": "tentacool"}, "version_details": []}
        ],
    })

    # Region -- template needs: name, main_generation.name, pokedexes[],
    #   version_groups[], locations[]
    mock_api.register("region", 1, {
        "name": "kanto", "id": 1,
        "main_generation": {"name": "generation-i", "url": "https://pokeapi.co/api/v2/generation/1/"},
        "locations": [{"name": "cerulean-city"}, {"name": "vermilion-city"}],
        "pokedexes": [{"name": "kanto", "url": "https://pokeapi.co/api/v2/pokedex/2/"}],
        "version_groups": [{"name": "red-blue", "url": "https://pokeapi.co/api/v2/version-group/1/"}],
        "names": [{"name": "Kanto", "language": {"name": "en"}}],
    })
    mock_api.register("region", "kanto", mock_api.responses[("region", "1")])

    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "canalave-city"}], "count": 1, "next": None,
    }


class TestLocationRoutes:
    def test_location_list(self, client):
        response = client.get("/location/")
        assert response.status_code == 200

    def test_location_detail_by_id(self, client):
        response = client.get("/location/1")
        assert response.status_code == 200

    def test_location_detail_by_name(self, client):
        response = client.get("/location/canalave-city")
        assert response.status_code == 200

    def test_location_not_found(self, client):
        response = client.get("/location/nonexistent")
        assert response.status_code in (400, 404)


class TestLocationAreaRoutes:
    def test_location_area_detail_by_id(self, client):
        response = client.get("/location-area/1")
        assert response.status_code == 200

    def test_location_area_not_found(self, client):
        response = client.get("/location-area/99999")
        assert response.status_code in (400, 404)


class TestRegionRoutes:
    def test_region_list(self, client):
        response = client.get("/region/")
        assert response.status_code == 200

    def test_region_detail_by_id(self, client):
        response = client.get("/region/1")
        assert response.status_code == 200

    def test_region_detail_by_name(self, client):
        response = client.get("/region/kanto")
        assert response.status_code == 200

    def test_region_not_found(self, client):
        response = client.get("/region/nonexistent")
        assert response.status_code in (400, 404)


class TestSpriteRouteConflict:
    """Verify that pal-park-area URLs are intercepted by the sprite blueprint.
    pal-park-area has no dedicated route.

    This documents a known bug -- see Phase 1 plan.
    """

    def test_pal_park_area_intercepted_by_sprite_route(self, client):
        response = client.get("/pal-park-area/1")
        assert response.status_code == 400

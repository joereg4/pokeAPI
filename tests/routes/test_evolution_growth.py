"""
Tests for the evolution_growth blueprint routes.

All external API calls are mocked.

growth-rate and gender are served by the generic handler in utilities.py
(now reachable after sprite prefix fix).
"""

import pytest


@pytest.fixture(autouse=True)
def setup_mocks(mock_api, mock_requests):
    """Register mock responses for generation, growth-rate, and gender."""
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

    # Growth rate -- served by generic route
    mock_api.register("growth-rate", 1, {
        "name": "slow", "id": 1,
        "formula": "\\frac{5x^3}{4}",
        "pokemon_species": [{"name": "bulbasaur"}],
        "levels": [{"level": 1, "experience": 0}, {"level": 100, "experience": 1250000}],
        "descriptions": [{"description": "slow", "language": {"name": "en"}}],
    })
    mock_api.register("growth-rate", "slow", mock_api.responses[("growth-rate", "1")])

    # Gender -- served by generic route
    mock_api.register("gender", 1, {
        "name": "female", "id": 1,
        "pokemon_species_details": [
            {"rate": 1, "pokemon_species": {"name": "bulbasaur"}}
        ],
    })
    mock_api.register("gender", "female", mock_api.responses[("gender", "1")])

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
        assert response.status_code == 404


class TestGrowthRateRoutes:
    """Growth rate served by generic route."""

    def test_growth_rate_detail_by_id(self, client):
        response = client.get("/growth-rate/1")
        assert response.status_code == 200

    def test_growth_rate_detail_by_name(self, client):
        response = client.get("/growth-rate/slow")
        assert response.status_code == 200

    def test_growth_rate_not_found(self, client):
        response = client.get("/growth-rate/nonexistent")
        assert response.status_code == 404


class TestGenderRoutes:
    """Gender served by generic route."""

    def test_gender_detail_by_id(self, client):
        response = client.get("/gender/1")
        assert response.status_code == 200

    def test_gender_detail_by_name(self, client):
        response = client.get("/gender/female")
        assert response.status_code == 200

    def test_gender_not_found(self, client):
        response = client.get("/gender/nonexistent")
        assert response.status_code == 404

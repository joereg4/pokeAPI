"""
Tests for evolution and breeding (egg group) routes.

All external API calls are mocked.

evolution-chain and evolution-trigger are served by the generic handler
in utilities.py (now reachable after sprite prefix fix).
"""

import pytest


@pytest.fixture(autouse=True)
def setup_mocks(mock_api, mock_requests):
    """Register mock responses for evolution and breeding endpoints."""
    # Evolution chain -- served by generic route
    mock_api.register("evolution-chain", 1, {
        "id": 1,
        "chain": {
            "species": {"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon-species/1/"},
            "evolves_to": [
                {
                    "species": {"name": "ivysaur", "url": "https://pokeapi.co/api/v2/pokemon-species/2/"},
                    "evolution_details": [
                        {
                            "gender": None, "held_item": None, "known_move": None,
                            "known_move_type": None, "location": None, "min_level": 16,
                            "min_happiness": None, "min_beauty": None, "min_affection": None,
                            "needs_overworld_rain": False, "party_species": None,
                            "party_type": None, "relative_physical_stats": None,
                            "time_of_day": "", "trade_species": None, "turn_upside_down": False,
                            "trigger": {"name": "level-up", "url": "https://pokeapi.co/api/v2/evolution-trigger/1/"},
                        }
                    ],
                    "evolves_to": [],
                }
            ],
            "evolution_details": [],
        },
    })

    # Evolution trigger -- served by generic route
    mock_api.register("evolution-trigger", 1, {
        "name": "level-up", "id": 1,
        "pokemon_species": [{"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon-species/1/"}],
        "names": [{"name": "Level up", "language": {"name": "en"}}],
    })
    mock_api.register("evolution-trigger", "level-up", mock_api.responses[("evolution-trigger", "1")])

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


class TestEvolutionChainRoutes:
    """evolution-chain served by generic route. Accepts int IDs and names."""

    def test_evolution_chain_detail(self, client):
        response = client.get("/evolution-chain/1")
        assert response.status_code == 200

    def test_evolution_chain_not_found(self, client):
        response = client.get("/evolution-chain/99999")
        assert response.status_code == 404


class TestEvolutionTriggerRoutes:
    """evolution-trigger served by generic route."""

    def test_trigger_detail_by_id(self, client):
        response = client.get("/evolution-trigger/1")
        assert response.status_code == 200

    def test_trigger_detail_by_name(self, client):
        response = client.get("/evolution-trigger/level-up")
        assert response.status_code == 200

    def test_trigger_not_found(self, client):
        response = client.get("/evolution-trigger/nonexistent")
        assert response.status_code == 404


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
        assert response.status_code == 404

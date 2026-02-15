import pytest
from app import create_app
import json
from requests.exceptions import HTTPError
from test_helper import load_mock_data
from utils import get_cache_stats, warm_common_endpoints
from flask_limiter.errors import RateLimitExceeded
from unittest.mock import patch
from models.model import db


@pytest.fixture
def client():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 300,
        "RATELIMIT_ENABLED": False,  # Disable rate limiting globally
    }
    app = create_app(test_config)

    # Disable rate limiting for all endpoints
    from limiter import limiter

    limiter.enabled = False

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def mock_limiter(mocker):
    """Mock the rate limiter to prevent rate limit errors in tests."""
    with patch("flask_limiter.extension.Limiter.current_limit", return_value=None):
        with patch("flask_limiter.extension.Limiter.check", return_value=True):
            with patch("flask_limiter.extension.Limiter.reset", return_value=None):
                yield


def test_pokemon_index_route(client):
    response = client.get("/")
    assert response.status_code == 200

    # Check for key elements in the homepage HTML
    assert (
        "Welcome to the Pokédex API".encode("utf-8") in response.data
    )  # Check for welcome message
    assert b"Get Started" in response.data  # Check for 'Get Started' button
    assert (
        "Featured Pokémon".encode("utf-8") in response.data
    )  # Check for featured Pokémon section


def test_detective_pikachu_route(client):
    response = client.get("/detective-pikachu")
    assert response.status_code == 200


def test_pokedex_route(client):
    # Test pokedex list
    response = client.get("/pokedex/")
    assert response.status_code == 200

    # Test with ID
    response = client.get("/pokedex/20")
    assert response.status_code == 200

    # Test with name
    response = client.get("/pokedex/hoenn")
    assert response.status_code == 200

    # Test non-existent pokedex
    response = client.get("/pokedex/nonexistent")
    assert response.status_code == 404


def test_pokemon_list_route(client):
    response = client.get("/pokemon/")
    assert response.status_code == 200


def test_pokemon_detail_route(client, mocker):
    """Test the Pokémon detail route with a redirect."""
    # Mock successful Pokémon data fetch
    mock_pokemon_data = {
        "name": "bulbasaur",
        "id": 1,
        "sprites": {
            "front_default": "some_url",
            "other": {"official-artwork": {"front_default": "some_url"}},
        },
        "species": {
            "name": "bulbasaur",
            "url": "https://pokeapi.co/api/v2/pokemon-species/1/",
        },
        "base_experience": 64,
        "height": 7,
        "weight": 69,
        "is_default": True,
        "order": 1,
        "abilities": [],
        "moves": [
            {
                "move": {"name": "tackle", "url": "some_url"},
                "version_group_details": [
                    {"move_learn_method": {"name": "level-up"}, "level_learned_at": 1}
                ],
            }
        ],
        "held_items": [],
        "types": [{"type": {"name": "grass", "url": "some_url"}}],
        "stats": [],
    }

    # Mock species data
    mock_species_data = {
        "name": "bulbasaur",
        "id": 1,
        "names": [{"name": "Bulbasaur", "language": {"name": "en"}}],
        "habitat": {"name": "grassland"},
        "shape": {"name": "quadruped"},
        "color": {"name": "green"},
        "flavor_text_entries": [
            {
                "flavor_text": "Test description",
                "language": {"name": "en"},
                "version": {"name": "red"},
            }
        ],
        "pokedex_numbers": [
            {
                "entry_number": 1,
                "pokedex": {
                    "name": "national",
                    "url": "https://pokeapi.co/api/v2/pokedex/1/",
                },
            }
        ],
        "evolution_chain": {"url": "https://pokeapi.co/api/v2/evolution-chain/1/"},
    }

    # Mock palafin species data
    mock_palafin_species_data = {
        "name": "palafin",
        "id": 964,
        "names": [{"name": "Palafin", "language": {"name": "en"}}],
        "habitat": {"name": "sea"},
        "shape": {"name": "fish"},
        "color": {"name": "blue"},
        "flavor_text_entries": [
            {
                "flavor_text": "Test description",
                "language": {"name": "en"},
                "version": {"name": "scarlet"},
            }
        ],
        "pokedex_numbers": [
            {
                "entry_number": 964,
                "pokedex": {
                    "name": "national",
                    "url": "https://pokeapi.co/api/v2/pokedex/1/",
                },
            }
        ],
        "evolution_chain": {"url": "https://pokeapi.co/api/v2/evolution-chain/964/"},
    }

    # Mock evolution chain data
    mock_evolution_chain_data = {
        "chain": {
            "species": {
                "name": "palafin",
                "url": "https://pokeapi.co/api/v2/pokemon-species/964/",
            },
            "evolves_to": [],
            "evolution_details": [],
            "is_baby": False,
        },
        "id": 964,
    }

    # Mock evolution chain list
    mock_evolution_chain_list = [
        {
            "name": "palafin",
            "species_id": 964,
            "sprite": "some_url",
            "min_level": None,
            "trigger": None,
        }
    ]

    # Mock the API call to handle both palfin and palafin
    def mock_fetch_data_with_error(endpoint, resource_id):
        if resource_id == "palfin":
            from requests.exceptions import HTTPError

            response = mocker.Mock()
            response.status_code = 404
            raise HTTPError("404 Client Error", response=response)
        elif endpoint == "pokemon-species" and (
            resource_id == "palafin" or resource_id == "PALAFIN"
        ):
            return mock_palafin_species_data
        elif endpoint == "evolution-chain" and (
            resource_id == "964" or resource_id == 964
        ):
            return mock_evolution_chain_data
        elif endpoint == "evolution-chain" and (resource_id == "1" or resource_id == 1):
            return {
                "chain": {
                    "species": {
                        "name": "bulbasaur",
                        "url": "https://pokeapi.co/api/v2/pokemon-species/1/",
                    },
                    "evolves_to": [],
                    "evolution_details": [],
                    "is_baby": False,
                },
                "id": 1,
            }
        elif resource_id == "palafin" or resource_id == "PALAFIN":
            # Mock data for the Pokemon endpoint
            return {
                "name": "palafin",
                "id": 964,
                "sprites": {
                    "front_default": "some_url",
                    "other": {"official-artwork": {"front_default": "some_url"}},
                },
                "species": {
                    "name": "palafin",
                    "url": "https://pokeapi.co/api/v2/pokemon-species/964/",
                },
                "base_experience": 160,
                "height": 13,
                "weight": 97,
                "is_default": True,
                "order": 964,
                "abilities": [],
                "moves": [],
                "held_items": [],
                "types": [{"type": {"name": "water", "url": "some_url"}}],
                "stats": [],
            }
        elif endpoint == "type" and resource_id == "water":
            # Mock type data for water
            return {
                "name": "water",
                "damage_relations": {
                    "double_damage_to": [],
                    "half_damage_to": [],
                    "no_damage_to": [],
                    "double_damage_from": [],
                    "half_damage_from": [],
                    "no_damage_from": [],
                },
            }
        elif endpoint == "type" and resource_id == "grass":
            # Mock type data for grass
            return {
                "name": "grass",
                "damage_relations": {
                    "double_damage_to": [{"name": "water", "url": "some_url"}],
                    "half_damage_to": [{"name": "fire", "url": "some_url"}],
                    "no_damage_to": [],
                    "double_damage_from": [{"name": "fire", "url": "some_url"}],
                    "half_damage_from": [{"name": "water", "url": "some_url"}],
                    "no_damage_from": [],
                },
            }
        elif endpoint == "pokemon" and (resource_id == "1" or resource_id == 1):
            return mock_pokemon_data
        elif endpoint == "pokemon-species" and (resource_id == "1" or resource_id == 1):
            return mock_species_data
        return None

    mocker.patch(
        "pokedex.APIResource.fetch_data", side_effect=mock_fetch_data_with_error
    )
    mocker.patch("pokedex.get_chain", return_value=mock_evolution_chain_list)

    # Test redirect for palfin (misspelled) - should ultimately 404
    response = client.get("/pokemon/palfin")
    assert response.status_code == 302  # First redirect
    redirect_url = response.headers["Location"]
    response = client.get(redirect_url)
    assert response.status_code == 404  # Should 404 after redirect

    # Test case-insensitive palafin (correct spelling) - should succeed
    response = client.get("/pokemon/PALAFIN")
    assert response.status_code == 200  # Should succeed
    assert b"Palafin" in response.data  # Should contain the Pokemon name

    # Test with valid ID
    response = client.get("/pokemon/1")
    assert response.status_code == 200
    assert b"Bulbasaur" in response.data


def test_pokemon_color_route(client):
    # Test color list
    response = client.get("/pokemon-color/")
    assert response.status_code == 200

    # Test with ID
    response = client.get("/pokemon-color/1")
    assert response.status_code == 200

    # Test with name
    response = client.get("/pokemon-color/black")
    assert response.status_code == 200

    # Test non-existent color
    response = client.get("/pokemon-color/nonexistent")
    assert response.status_code == 404


def test_pokemon_habitat_route(client):
    # Test habitat list
    response = client.get("/pokemon-habitat/")
    assert response.status_code == 200

    # Test with ID
    response = client.get("/pokemon-habitat/1")
    assert response.status_code == 200

    # Test with name
    response = client.get("/pokemon-habitat/cave")
    assert response.status_code == 200

    # Test non-existent habitat
    response = client.get("/pokemon-habitat/nonexistent")
    assert response.status_code == 404


def test_pokemon_shape_route(client):
    # Test shape list
    response = client.get("/pokemon-shape/")
    assert response.status_code == 200

    # Test with ID
    response = client.get("/pokemon-shape/1")
    assert response.status_code == 200

    # Test with name
    response = client.get("/pokemon-shape/ball")
    assert response.status_code == 200

    # Test non-existent shape
    response = client.get("/pokemon-shape/nonexistent")
    assert response.status_code == 404


def test_pokemon_species_route(client, mocker):
    # Mock data for species list
    mock_species_list = {
        "results": [{"name": "bulbasaur"}, {"name": "charmander"}, {"name": "squirtle"}]
    }

    # Mock data for individual species
    mock_species_data = load_mock_data("minimal_species.json")

    # Mock pokemon data
    mock_pokemon_data = {
        "name": "bulbasaur",
        "id": 1,
        "sprites": {
            "front_default": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/1.png",
            "other": {
                "official-artwork": {
                    "front_default": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png"
                }
            },
        },
    }

    # Mock the API calls with conditional return values
    def mock_fetch_data(resource_type, identifier):
        if resource_type == "pokemon-species" and identifier in [1, "1", "bulbasaur"]:
            return mock_species_data
        elif resource_type == "pokemon" and identifier in [1, "1", "bulbasaur"]:
            return mock_pokemon_data
        from requests.exceptions import HTTPError

        response = mocker.Mock()
        response.status_code = 404
        response.url = f"https://pokeapi.co/api/v2/{resource_type}/{identifier}"
        raise HTTPError(
            f"{response.status_code} Client Error: Not Found for url: {response.url}",
            response=response,
        )

    mocker.patch("pokedex.APIResource.fetch_data", side_effect=mock_fetch_data)
    mocker.patch(
        "routes.pokemon.fetch_all_results", return_value=mock_species_list["results"]
    )

    # Test species list
    response = client.get("/pokemon-species/")
    assert response.status_code == 200

    # Test with ID
    response = client.get("/pokemon-species/1")
    assert response.status_code == 200

    # Test with name
    response = client.get("/pokemon-species/bulbasaur")
    assert response.status_code == 200

    # Test non-existent species
    response = client.get("/pokemon-species/nonexistent")
    assert response.status_code == 404


def test_type_route(client):
    # Test type list
    response = client.get("/type/")
    assert response.status_code == 200

    # Test with ID
    response = client.get("/type/1")
    assert response.status_code == 200

    # Test with name
    response = client.get("/type/normal")
    assert response.status_code == 200

    # Test non-existent type
    response = client.get("/type/nonexistent")
    assert response.status_code == 404

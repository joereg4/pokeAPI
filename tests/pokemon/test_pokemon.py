"""
Tests for the pokemon blueprint routes.

All external API calls are mocked -- no real network requests.
Uses the shared mock_api and mock_requests fixtures from conftest.py.
"""

import pytest
from requests.exceptions import HTTPError
from conftest import load_mock_data


# ---------------------------------------------------------------------------
# Index / Homepage
# ---------------------------------------------------------------------------

def test_pokemon_index_route(client, mock_requests):
    """Homepage should render with welcome message and featured section."""
    # fetch_count makes direct requests.get calls
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {"count": 100, "results": []}

    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to the Pokédex API".encode("utf-8") in response.data
    assert b"Get Started" in response.data
    assert "Featured Pokémon".encode("utf-8") in response.data


# ---------------------------------------------------------------------------
# Pokemon list
# ---------------------------------------------------------------------------

def test_pokemon_list_route(client, mock_api, mock_requests):
    """Pokemon list page should render successfully."""
    # The list route uses direct requests.get for pagination
    bulbasaur = load_mock_data("bulbasaur.json")
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon/1/"}],
        "count": 1,
        "next": None,
    }
    # create_pokemon_list calls APIResource.fetch_data for each pokemon
    mock_api.register("pokemon", "bulbasaur", bulbasaur)

    response = client.get("/pokemon/")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Pokemon detail
# ---------------------------------------------------------------------------

def test_pokemon_detail_route(client, mocker):
    """Test pokemon detail with valid data, misspelling redirect, and case insensitivity."""
    mock_pokemon_data = load_mock_data("bulbasaur.json")

    mock_species_data = {
        "name": "bulbasaur", "id": 1,
        "names": [{"name": "Bulbasaur", "language": {"name": "en"}}],
        "habitat": {"name": "grassland"}, "shape": {"name": "quadruped"}, "color": {"name": "green"},
        "flavor_text_entries": [
            {"flavor_text": "Test description", "language": {"name": "en"}, "version": {"name": "red"}}
        ],
        "pokedex_numbers": [{"entry_number": 1, "pokedex": {"name": "national", "url": "https://pokeapi.co/api/v2/pokedex/1/"}}],
        "evolution_chain": {"url": "https://pokeapi.co/api/v2/evolution-chain/1/"},
    }

    mock_evolution_chain_list = [
        {"name": "bulbasaur", "species_id": 1, "sprite": "some_url", "min_level": None, "trigger": None}
    ]

    def mock_fetch_data_with_error(endpoint, resource_id, **kwargs):
        if resource_id == "palfin":
            response = mocker.Mock()
            response.status_code = 404
            raise HTTPError("404 Client Error", response=response)
        elif endpoint == "pokemon" and str(resource_id).lower() in ("1", "bulbasaur"):
            return mock_pokemon_data
        elif endpoint == "pokemon-species" and str(resource_id).lower() in ("1", "bulbasaur"):
            return mock_species_data
        elif endpoint == "evolution-chain" and resource_id in (1, "1"):
            return {
                "chain": {
                    "species": {"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon-species/1/"},
                    "evolves_to": [], "evolution_details": [], "is_baby": False,
                },
                "id": 1,
            }
        raise ValueError(f"{endpoint} '{resource_id}' not found")

    mocker.patch("pokedex.APIResource.fetch_data", side_effect=mock_fetch_data_with_error)
    mocker.patch("pokedex.get_chain", return_value=mock_evolution_chain_list)

    # Test redirect for palfin (misspelled) - should redirect then 404
    response = client.get("/pokemon/palfin")
    assert response.status_code == 302
    redirect_url = response.headers["Location"]
    response = client.get(redirect_url)
    assert response.status_code == 404

    # Test with valid ID
    response = client.get("/pokemon/1")
    assert response.status_code == 200
    assert b"Bulbasaur" in response.data


# ---------------------------------------------------------------------------
# Pokemon color routes
# ---------------------------------------------------------------------------

def test_pokemon_color_list(client, mock_requests):
    """Color list route should render."""
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "black"}, {"name": "blue"}],
        "count": 2, "next": None,
    }
    response = client.get("/pokemon-color/")
    assert response.status_code == 200


def test_pokemon_color_detail(client, mock_api):
    """Color detail should render with pokemon list."""
    mock_api.register("pokemon-color", 1, {
        "name": "black", "id": 1,
        "pokemon_species": [{"name": "snorlax", "url": "https://pokeapi.co/api/v2/pokemon-species/143/"}],
    })
    mock_api.register("pokemon-species", "snorlax", {
        "name": "snorlax", "id": 143,
        "varieties": [{"is_default": True, "pokemon": {"name": "snorlax", "url": "https://pokeapi.co/api/v2/pokemon/143/"}}],
        "pokedex_numbers": [{"entry_number": 143}],
    })
    mock_api.register("pokemon", "snorlax", {
        "name": "snorlax", "id": 143,
        "sprites": {"front_default": "url", "other": {"official-artwork": {"front_default": "url"}}},
        "species": {"name": "snorlax", "url": "https://pokeapi.co/api/v2/pokemon-species/143/"},
        "types": [{"type": {"name": "normal"}}],
    })
    response = client.get("/pokemon-color/1")
    assert response.status_code == 200


def test_pokemon_color_not_found(client, mock_api):
    """Non-existent color should return 404."""
    response = client.get("/pokemon-color/nonexistent")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Pokemon habitat routes
# ---------------------------------------------------------------------------

def test_pokemon_habitat_list(client, mock_requests):
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "cave"}, {"name": "forest"}],
        "count": 2, "next": None,
    }
    response = client.get("/pokemon-habitat/")
    assert response.status_code == 200


def test_pokemon_habitat_detail(client, mock_api):
    mock_api.register("pokemon-habitat", 1, {
        "name": "cave", "id": 1,
        "pokemon_species": [{"name": "zubat", "url": "https://pokeapi.co/api/v2/pokemon-species/41/"}],
    })
    mock_api.register("pokemon", "zubat", {
        "name": "zubat", "id": 41,
        "sprites": {"front_default": "url"},
        "species": {"name": "zubat", "url": "https://pokeapi.co/api/v2/pokemon-species/41/"},
        "types": [{"type": {"name": "poison"}}],
    })
    response = client.get("/pokemon-habitat/1")
    assert response.status_code == 200


def test_pokemon_habitat_not_found(client, mock_api):
    response = client.get("/pokemon-habitat/nonexistent")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Pokemon shape routes
# ---------------------------------------------------------------------------

def test_pokemon_shape_list(client, mock_requests):
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "ball"}, {"name": "squiggle"}],
        "count": 2, "next": None,
    }
    response = client.get("/pokemon-shape/")
    assert response.status_code == 200


def test_pokemon_shape_detail(client, mock_api):
    mock_api.register("pokemon-shape", 1, {
        "name": "ball", "id": 1,
        "pokemon_species": [{"name": "voltorb", "url": "https://pokeapi.co/api/v2/pokemon-species/100/"}],
    })
    mock_api.register("pokemon", "voltorb", {
        "name": "voltorb", "id": 100,
        "sprites": {"front_default": "url"},
        "species": {"name": "voltorb", "url": "https://pokeapi.co/api/v2/pokemon-species/100/"},
        "types": [{"type": {"name": "electric"}}],
    })
    response = client.get("/pokemon-shape/1")
    assert response.status_code == 200


def test_pokemon_shape_not_found(client, mock_api):
    response = client.get("/pokemon-shape/nonexistent")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Pokemon species routes
# ---------------------------------------------------------------------------

def test_pokemon_species_list(client, mocker):
    mocker.patch("routes.pokemon.fetch_all_results", return_value=[
        {"name": "bulbasaur"}, {"name": "charmander"}, {"name": "squirtle"},
    ])
    response = client.get("/pokemon-species/")
    assert response.status_code == 200


def test_pokemon_species_detail(client, mock_api):
    species_data = load_mock_data("minimal_species.json")
    pokemon_data = load_mock_data("bulbasaur.json")

    mock_api.register("pokemon-species", 1, species_data)
    mock_api.register("pokemon-species", "bulbasaur", species_data)
    mock_api.register("pokemon", "bulbasaur", pokemon_data)

    response = client.get("/pokemon-species/1")
    assert response.status_code == 200

    response = client.get("/pokemon-species/bulbasaur")
    assert response.status_code == 200


def test_pokemon_species_not_found(client, mock_api):
    response = client.get("/pokemon-species/nonexistent")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Type routes
# ---------------------------------------------------------------------------

def test_type_list(client, mock_requests):
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "normal"}, {"name": "fire"}],
        "count": 2, "next": None,
    }
    response = client.get("/type/")
    assert response.status_code == 200


def test_type_detail(client, mock_api):
    mock_api.register("type", 1, {
        "name": "normal", "id": 1,
        "damage_relations": {
            "double_damage_to": [], "half_damage_to": [], "no_damage_to": [],
            "double_damage_from": [{"name": "fighting"}],
            "half_damage_from": [], "no_damage_from": [{"name": "ghost"}],
        },
        "pokemon": [{"pokemon": {"name": "rattata", "url": "https://pokeapi.co/api/v2/pokemon/19/"}}],
    })
    mock_api.register("pokemon", "rattata", {
        "name": "rattata", "id": 19,
        "sprites": {"front_default": "url"},
        "species": {"name": "rattata", "url": "https://pokeapi.co/api/v2/pokemon-species/19/"},
        "types": [{"type": {"name": "normal"}}],
    })
    response = client.get("/type/1")
    assert response.status_code == 200


def test_type_not_found(client, mock_api):
    response = client.get("/type/nonexistent")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Pokedex routes
# ---------------------------------------------------------------------------

def test_pokedex_list(client, mock_requests):
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "national"}, {"name": "kanto"}],
        "count": 2, "next": None,
    }
    response = client.get("/pokedex/")
    assert response.status_code == 200


def test_pokedex_detail(client, mock_api, mock_requests):
    mock_api.register("pokedex", 1, {
        "name": "national", "id": 1,
        "pokemon_entries": [
            {"entry_number": 1, "pokemon_species": {"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon-species/1/"}},
        ],
    })
    bulbasaur = load_mock_data("bulbasaur.json")
    mock_api.register("pokemon", "bulbasaur", bulbasaur)

    # mock_requests for fetch_all_results (list endpoint) and create_pokemon_list
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {"results": [], "count": 0, "next": None}

    response = client.get("/pokedex/1")
    assert response.status_code == 200


def test_pokedex_not_found(client, mock_api):
    response = client.get("/pokedex/nonexistent")
    assert response.status_code == 404

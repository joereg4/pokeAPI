import pytest
from app import create_app
import json
from requests.exceptions import HTTPError
from test_helper import load_mock_data


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


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
    # Mock successful Pokemon data fetch
    mock_pokemon_data = {
        "name": "bulbasaur",
        "id": 1,
        "sprites": {
            "front_default": "some_url",
            "other": {"official-artwork": {"front_default": "some_url"}},
        },
        "species": {"name": "bulbasaur", "url": "some_url"},
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

    # Mock type data
    mock_type_data = {
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

    # Mock species data
    mock_species_data = {
        "name": "bulbasaur",
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
        "evolution_chain": {"url": "some_url"},
        "habitat": {"name": "grassland"},
        "color": {"name": "green"},
        "shape": {"name": "quadruped"},
    }

    # Mock evolution chain data
    mock_evolution_chain_data = {
        "chain": {"species": {"name": "bulbasaur"}, "evolves_to": []}
    }

    def mock_fetch_data(endpoint, resource_id):
        if endpoint == "pokemon":
            return mock_pokemon_data
        elif endpoint == "type":
            return mock_type_data
        elif endpoint == "pokemon-species":
            return mock_species_data
        elif endpoint == "evolution-chain":
            return mock_evolution_chain_data
        return None

    mocker.patch("pokedex.APIResource.fetch_data", side_effect=mock_fetch_data)

    # Mock get_summary function
    mocker.patch("pokedex.helper.get_summary", return_value="A test summary")

    # Mock get_pokemon_cards function
    mocker.patch("pokedex.helper.get_pokemon_cards", return_value=[])

    # Mock get_species_id_from_url function
    mocker.patch("pokedex.get_species_id_from_url", return_value=1)

    # Mock get_chain function
    mocker.patch("pokedex.get_chain", return_value=[])

    # Mock get_official_artwork function
    mocker.patch("pokedex.get_official_artwork", return_value="some_url")

    # Mock get_path function
    mocker.patch("pokedex.helper.get_path", return_value="mock_path")

    # Mock pandas read_csv
    class MockDataFrame:
        def __init__(self):
            self.empty = False
            self._name_series = MockSeries("bulbasaur")
            self._data = {"name": self._name_series}

        def __getitem__(self, key):
            if isinstance(key, str):
                return self._data.get(key, self)
            # Handle boolean indexing
            return MockDataFrame()

        @property
        def str(self):
            return self

        def lower(self):
            return self._name_series

        @property
        def iloc(self):
            return self

        def __getattr__(self, name):
            return self

        def __len__(self):
            return 1

    class MockSeries:
        def __init__(self, value):
            self.value = value

        @property
        def str(self):
            return self

        def lower(self):
            return self.value.lower()

        def __eq__(self, other):
            if isinstance(other, str):
                return self.value.lower() == other.lower()
            return False

    mocker.patch("pandas.read_csv", return_value=MockDataFrame())

    # Test with valid ID
    response = client.get("/pokemon/1")
    assert response.status_code == 200

    # Test with valid name
    response = client.get("/pokemon/bulbasaur")
    assert response.status_code == 200

    # Test with non-existent Pokemon
    def mock_fetch_none(endpoint, resource_id):
        return None

    mocker.patch("pokedex.APIResource.fetch_data", side_effect=mock_fetch_none)
    response = client.get("/pokemon/nonexistent")
    assert response.status_code == 404


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


def test_pokemon_form_route(client):
    # Test with ID
    response = client.get("/pokemon-form/1")
    assert response.status_code == 200

    # Test with name
    response = client.get("/pokemon-form/bulbasaur")
    assert response.status_code == 200

    # Test non-existent form
    response = client.get("/pokemon-form/nonexistent")
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

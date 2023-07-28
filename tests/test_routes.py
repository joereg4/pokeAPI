import pytest
import json
from unittest.mock import patch
from app import create_app


@pytest.fixture
def client():
    app = create_app({
        'TESTING': True,
        'DEBUG_PRINT_ROUTES': False
    })
    with app.test_client() as client:
        yield client


@pytest.fixture
def read_mock_data(file_name):
    with open(f"mock_data/{file_name}", 'r') as file:
        return json.load(file)


def test_app_creation(client):
    # Just a basic test to check if the app was created
    assert client


def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Expected Text from index.html" in response.data


@patch('requests.get')
def test_get_pokemon_list_route(mock_get, client):
    mock_data = {
        "results": [
            {
                "name": "bulbasaur",
                "url": "sample_url_for_bulbasaur"
            }
        ]
    }
    mock_get.return_value.json.return_value = mock_data

    response = client.get('/pokemon/')
    assert response.status_code == 200
    assert b"bulbasaur" in response.data


@patch('utils.APIResource.fetch_data')
@patch('utils.pokemon_species')
@patch('utils.get_species_id_from_url')
@patch('utils.evolution_chain')
@patch('utils.get_chain')
def test_get_pokemon_detail_route(mock_get_chain, mock_evolution_chain, mock_species_id_url, mock_species,
                                  mock_fetch_data, client):
    # Define mock return values using the read_mock_data function
    mock_fetch_data.return_value = read_mock_data("bulbasaur.json")
    mock_species.return_value = read_mock_data("species.txt")
    mock_species_id_url.return_value = 1
    mock_evolution_chain.return_value = read_mock_data("evolution_chain.txt")
    mock_get_chain.return_value = read_mock_data("get_chain.txt")

    response = client.get('/pokemon/bulbasaur')
    assert response.status_code == 200
    assert b"bulbasaur" in response.data

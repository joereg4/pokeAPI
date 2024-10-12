from unittest.mock import patch

import pytest

from tests.test_helper import get_test_client, load_mock_data, assert_response_status


@pytest.fixture
def client():
    return get_test_client()


def test_index_route(client):
    """Test the index route for the homepage."""
    response = client.get('/')
    assert response.status_code == 200  # Check if the page loads successfully

    # Check for key elements in the homepage HTML
    assert 'Welcome to the Pokédex API'.encode('utf-8') in response.data  # Check for welcome message
    assert b'Get Started' in response.data  # Check for 'Get Started' button
    assert 'Featured Pokémon'.encode('utf-8') in response.data  # Check for featured Pokémon section


def test_ability_list(client):
    """Test the ability list route with real mock data from file."""
    # Load mock data for abilities
    ability_data = load_mock_data('ability.json')

    # Patch the function that fetches data from the API in the route
    with patch('pokedex.helper.fetch_all_results') as mock_fetch_all_results:
        mock_fetch_all_results.return_value = ability_data['results']  # Use the results from the mock data

        # Make the request to the ability list route
        response = client.get('/ability/')

        # Check if the page loads successfully
        assert_response_status(response, expected_status=200)

        # Validate that known abilities from the mock data are in the response
        assert b'stench' in response.data  # Ability 1 from the mock data
        assert b'drizzle' in response.data  # Ability 2 from the mock data
        assert b'speed-boost' in response.data  # Ability 3 from the mock data


def test_valid_ability_detail(client):
    """Test the ability detail route with a valid ability ID."""
    # Load mock data for ability "stench"
    ability_data = load_mock_data('stench_ability.json')  # This file should contain mock data for the 'stench' ability

    # Patch the fetch_data function to return the mock ability data
    with patch('pokedex.APIResource.fetch_data') as mock_fetch_data:
        mock_fetch_data.return_value = ability_data  # Mocked data for ability ID 1 (stench)

        # Make the request to the ability detail route
        response = client.get('/ability/1')

        # Check if the page loads successfully
        assert_response_status(response, expected_status=200)

        # Validate that the 'stench' ability is present in the HTML
        assert b'stench' in response.data  # Assuming 'stench' is the ability with ID 1


def test_invalid_ability_detail(client):
    """Test the ability detail route with an invalid ability ID."""
    # Patch the fetch_data function to simulate a 404 scenario for an invalid ability
    with patch('pokedex.APIResource.fetch_data') as mock_fetch_data:
        mock_fetch_data.side_effect = ValueError("Ability not found")  # Simulate an invalid ability

        # Make the request to an invalid ability ID
        response = client.get('/ability/9999')  # Assume 9999 is invalid

        # Ensure the response is a 404 for invalid IDs
        assert response.status_code == 404
        assert b'Ability' in response.data and b'not found' in response.data  # Check for 404 message


def test_pokemon_list(client):
    """Test the Pokémon list route."""
    response = client.get('/pokemon/')
    assert response.status_code == 200  # Page loads successfully

    # Check for key elements in the HTML response
    assert b'Pok\xc3\xa9mon' in response.data  # Check for the word 'Pokémon' (with UTF-8 encoding)
    assert b'Bulbasaur' in response.data  # Check if 'Bulbasaur' is in the list of Pokémon


def test_valid_pokemon_detail(client):
    """Test the Pokémon detail route with all API calls mocked."""

    # Load mock data for different API responses
    pokemon_data = load_mock_data('bulbasaur.json')
    type_data = load_mock_data('grass_type.json')
    species_data = load_mock_data('bulbasaur_species.json')
    evolution_data = load_mock_data('bulbasaur_evolution_chain.json')

    # Patch multiple external API calls
    with patch('pokedex.APIResource.fetch_data') as mock_fetch_data, \
            patch('pokedex.pokemon_species') as mock_pokemon_species, \
            patch('pokedex.evolution_chain') as mock_evolution_chain, \
            patch('pokedex.get_chain') as mock_get_chain:

        # Define side effects for fetch_data based on the resource being requested
        def fetch_data_side_effect(resource, id_or_name):
            if resource == 'pokemon':
                return pokemon_data
            elif resource == 'type':
                return type_data
            else:
                return {}

        mock_fetch_data.side_effect = fetch_data_side_effect
        mock_pokemon_species.return_value = species_data
        mock_evolution_chain.return_value = evolution_data
        mock_get_chain.return_value = {"name": "Bulbasaur", "evolves_to": []}

        response = client.get('/pokemon/bulbasaur')

        # Check that the response is 200 OK
        assert_response_status(response, expected_status=200)

        # Validate that key parts of the HTML contain the correct data
        assert b'Bulbasaur' in response.data
        assert b'Base Experience: 64' in response.data
        assert b'Height: 7' in response.data
        assert b'Weight: 69' in response.data
        assert b'overgrow' in response.data


def test_invalid_pokemon_detail(client):
    """Test the Pokémon detail route with an invalid Pokémon ID."""
    response = client.get('/pokemon/invalid_pokemon')  # Invalid Pokémon ID
    assert response.status_code == 404  # Ensure the response is a 404


def test_static_resources_integration(client):
    """Test that CSS and JS files are properly linked in the HTML."""
    response = client.get('/')  # or any other route that includes the base template

    # Assert that the response status is OK
    assert response.status_code == 200

    # Check for CSS file link
    assert b'<link rel="stylesheet" href="/static/css/styles.css">' in response.data

    # Check for JavaScript file link
    assert b'<script src="/static/js/search.js"></script>' in response.data

    # Optionally, check for Bootstrap or other resources if needed
    assert b'<link rel="stylesheet" href="/static/css/bootstrap.css">' in response.data
    assert b'<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>' in response.data

import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_pokemon_index_route(client):
    response = client.get('/')
    assert response.status_code == 200

    # Check for key elements in the homepage HTML
    assert 'Welcome to the Pokédex API'.encode('utf-8') in response.data  # Check for welcome message
    assert b'Get Started' in response.data  # Check for 'Get Started' button
    assert 'Featured Pokémon'.encode('utf-8') in response.data  # Check for featured Pokémon section

def test_detective_pikachu_route(client):
    response = client.get('/detective-pikachu')
    assert response.status_code == 200

def test_pokedex_route(client):
    # Test pokedex list
    response = client.get('/pokedex/')
    assert response.status_code == 200

    # Test with ID
    response = client.get('/pokedex/20')
    assert response.status_code == 200

    # Test with name
    response = client.get('/pokedex/hoenn')
    assert response.status_code == 200

    # Test non-existent pokedex
    response = client.get('/pokedex/nonexistent')
    assert response.status_code == 404

def test_pokemon_list_route(client):
    response = client.get('/pokemon/')
    assert response.status_code == 200

def test_pokemon_detail_route(client):
    # Test with ID
    response = client.get('/pokemon/1')
    assert response.status_code == 200

    # Test with name
    response = client.get('/pokemon/bulbasaur')
    assert response.status_code == 200

    # Test non-existent pokemon
    response = client.get('/pokemon/nonexistent')
    assert response.status_code == 404

def test_pokemon_color_route(client):
    # Test color list
    response = client.get('/pokemon-color/')
    assert response.status_code == 200

    # Test with ID
    response = client.get('/pokemon-color/1')
    assert response.status_code == 200

    # Test with name
    response = client.get('/pokemon-color/black')
    assert response.status_code == 200

    # Test non-existent color
    response = client.get('/pokemon-color/nonexistent')
    assert response.status_code == 404

def test_pokemon_form_route(client):
    # Test with ID
    response = client.get('/pokemon-form/1')
    assert response.status_code == 200

    # Test with name
    response = client.get('/pokemon-form/bulbasaur')
    assert response.status_code == 200

    # Test non-existent form
    response = client.get('/pokemon-form/nonexistent')
    assert response.status_code == 404

def test_pokemon_habitat_route(client):
    # Test habitat list
    response = client.get('/pokemon-habitat/')
    assert response.status_code == 200

    # Test with ID
    response = client.get('/pokemon-habitat/1')
    assert response.status_code == 200

    # Test with name
    response = client.get('/pokemon-habitat/cave')
    assert response.status_code == 200

    # Test non-existent habitat
    response = client.get('/pokemon-habitat/nonexistent')
    assert response.status_code == 404

def test_pokemon_shape_route(client):
    # Test shape list
    response = client.get('/pokemon-shape/')
    assert response.status_code == 200

    # Test with ID
    response = client.get('/pokemon-shape/1')
    assert response.status_code == 200

    # Test with name
    response = client.get('/pokemon-shape/ball')
    assert response.status_code == 200

    # Test non-existent shape
    response = client.get('/pokemon-shape/nonexistent')
    assert response.status_code == 404

def test_pokemon_species_route(client):
    # Test species list
    response = client.get('/pokemon-species/')
    assert response.status_code == 200

    # Test with ID
    response = client.get('/pokemon-species/1')
    assert response.status_code == 200

    # Test with name
    response = client.get('/pokemon-species/bulbasaur')
    assert response.status_code == 200

    # Test non-existent species
    response = client.get('/pokemon-species/nonexistent')
    assert response.status_code == 404

def test_type_route(client):
    # Test type list
    response = client.get('/type/')
    assert response.status_code == 200

    # Test with ID
    response = client.get('/type/1')
    assert response.status_code == 200

    # Test with name
    response = client.get('/type/normal')
    assert response.status_code == 200

    # Test non-existent type
    response = client.get('/type/nonexistent')
    assert response.status_code == 404

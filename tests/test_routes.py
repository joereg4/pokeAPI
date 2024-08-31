import pytest
from flask import url_for
import json
from unittest.mock import patch
from app import create_app


@pytest.fixture
def client():
    app = create_app({
        'TESTING': True,
        'DEBUG_PRINT_ROUTES': False
    })
    return app.test_client()


@pytest.fixture
def read_mock_data():
    def _read(file_name):
        with open(f"mock_data/{file_name}", 'r') as file:
            return json.load(file)

    return _read


def test_app_creation(client):
    # Just a basic test to check if the app was created
    assert client


def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200


def test_get_pokemon_detail_route(client):
    response = client.get('/pokemon/bulbasaur')
    assert response.status_code == 200
    assert b"bulbasaur" in response.data


def test_home_page(client):
    with client.application.test_request_context():
        # Test if the home page loads correctly
        response = client.get(url_for('pokemon.index'))
        assert response.status_code == 200
        assert "Welcome to the Pokédex API".encode('utf-8') in response.data
        assert b"Get Started" in response.data

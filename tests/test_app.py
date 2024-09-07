import pytest
from flask import url_for

from tests.test_helper import get_test_client, assert_response_status


@pytest.fixture
def client():
    return get_test_client()


def test_app_creation(client):
    # Test if the app was created successfully
    assert client


def test_home_page(client):
    with client.application.test_request_context():
        response = client.get(url_for('pokemon.index'))
        assert_response_status(response)
        assert "Welcome to the Pokédex API".encode('utf-8') in response.data
        assert b"Get Started" in response.data

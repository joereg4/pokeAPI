from pytest import fixture
from flask import url_for

from tests.test_helper import get_test_client, assert_response_status


@fixture
def client():
    return get_test_client()


def test_app_creation(client):
    # Test if the app was created successfully
    assert client


def test_home_page(client):
    """Test the homepage for correct elements and response"""
    with client.application.test_request_context():
        # Send request to the homepage
        response = client.get(url_for('pokemon.index'))

        # Assert that the page loads successfully
        assert_response_status(response, expected_status=200)
        assert response.status_code == 200

        # Check for key elements on the homepage
        assert "Welcome to the Pokédex API".encode('utf-8') in response.data
        assert b"Get Started" in response.data

        # Check that the page title is correct
        assert b"<title>Home - Pok\xc3\xa9dex API</title>" in response.data

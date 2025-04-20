from pytest import fixture
from flask import url_for

from tests.test_helper import get_test_client, assert_response_status
from utils import get_cache_stats, warm_common_endpoints


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
        response = client.get(url_for("pokemon.index"))

        # Assert that the page loads successfully
        assert_response_status(response, expected_status=200)
        assert response.status_code == 200

        # Check for key elements on the homepage
        assert "Welcome to the Pokédex API".encode("utf-8") in response.data
        assert b"Get Started" in response.data

        # Check that the page title is correct
        assert b"<title>Home - Pok\xc3\xa9dex API</title>" in response.data


def test_index_counts(client, mocker):
    # Mock the fetch_count function to return actual counts for each endpoint
    def mock_fetch_count(endpoint):
        counts = {
            "pokemon": 1302,
            "ability": 367,
            "type": 21,
            "pokemon-color": 10,
            "pokemon-habitat": 9,
        }
        return endpoint, counts.get(endpoint, 0)

    mocker.patch("routes.pokemon.fetch_count", side_effect=mock_fetch_count)

    # Make request to index page
    with client.application.test_request_context():
        response = client.get(url_for("pokemon.index"))
        assert response.status_code == 200

        # Check that the response contains the correct counts for resources
        html = response.data.decode()
        # Check for the presence of the count values in the HTML
        assert "1302" in html
        assert "367" in html
        assert "21" in html
        assert "10" in html
        assert "9" in html

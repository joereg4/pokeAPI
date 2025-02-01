import pytest
from flask import url_for, abort
from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    app.config["RATELIMIT_ENABLED"] = False

    # Create test routes that trigger specific errors
    @app.route("/test-403")
    def trigger_403():
        abort(403)

    @app.route("/test-404")
    def trigger_404():
        abort(404)

    @app.route("/test-500")
    def trigger_500():
        abort(500)

    @app.route("/test-429")
    def trigger_429():
        abort(429)

    with app.test_client() as test_client:
        with app.app_context():
            yield test_client


def test_403_error_page(client):
    """Test the 403 Forbidden error page"""
    response = client.get("/test-403")
    assert response.status_code == 403
    assert b"403" in response.data
    assert b"Forbidden" in response.data


def test_404_error_page(client):
    """Test the 404 Not Found error page"""
    response = client.get("/test-404")
    assert response.status_code == 404
    assert b"404" in response.data
    assert b"The requested URL was not found on the server" in response.data


def test_404_error_page_with_custom_message(client):
    """Test the 404 page with a custom error message"""
    response = client.get("/nonexistent-path")
    assert response.status_code == 404
    assert b"404" in response.data
    assert b"The requested URL was not found on the server" in response.data


def test_500_error_page(client):
    """Test the 500 Internal Server Error page"""
    response = client.get("/test-500")
    assert response.status_code == 500
    assert b"500" in response.data
    assert b"An internal server error occurred" in response.data
    assert b"Our team has been notified" in response.data


def test_429_error_page(client):
    """Test the 429 Too Many Requests error page"""
    response = client.get("/test-429")
    assert response.status_code == 429
    assert b"Rate Limit Exceeded" in response.data
    assert (
        b"Please try again later or consider upgrading your API plan" in response.data
    )


def test_error_pages_have_home_link(client):
    """Test that all error pages have a working home link"""
    error_routes = ["/test-403", "/test-404", "/test-500", "/test-429"]

    for route in error_routes:
        response = client.get(route)
        assert b'href="' in response.data
        # All error pages should have a link back to some form of home page
        assert any(
            home_link in response.data
            for home_link in [
                b"pokemon/?page=1",
                b"pokemon.index",
                b"Return Home",
                b"Go to Home",
            ]
        )

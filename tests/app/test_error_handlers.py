import pytest
from flask import url_for, abort
from app import create_app
from model import db


@pytest.fixture
def client():
    """Create a test client."""
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
    }
    app = create_app(test_config)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_403_error_page(client):
    """Test the 403 Forbidden error page"""
    response = client.get("/test-403")
    assert response.status_code == 403
    assert b"403" in response.data
    assert b"Forbidden" in response.data
    assert b'class="text-danger display-2' in response.data


def test_404_error_page(client):
    """Test the 404 Not Found error page"""
    response = client.get("/test-404")
    assert response.status_code == 404
    assert b"404" in response.data
    assert b"The requested URL was not found on the server" in response.data
    assert b'class="text-warning display-2' in response.data


def test_404_error_page_with_custom_message(client):
    """Test the 404 page with a custom error message"""
    response = client.get("/nonexistent-path")
    assert response.status_code == 404
    assert b"404" in response.data
    assert b"The requested URL was not found on the server" in response.data
    assert b'class="text-warning display-2' in response.data


def test_500_error_page(client):
    """Test the 500 Internal Server Error page"""
    response = client.get("/test-500")
    assert response.status_code == 500
    assert b"500" in response.data
    assert b"An internal server error occurred" in response.data
    assert b"Our team has been notified" in response.data
    assert b'class="text-danger display-2' in response.data


def test_429_error_page(client):
    """Test the 429 Too Many Requests error page"""
    response = client.get("/test-429")
    assert response.status_code == 429
    assert b"429" in response.data
    assert b"Rate Limit Exceeded" in response.data
    assert (
        b"Please try again later or consider upgrading your API plan" in response.data
    )
    assert b'class="text-danger display-2' in response.data
    assert b"fas fa-exclamation-circle" in response.data
    assert b"Check API Status" in response.data


def test_error_pages_have_consistent_design(client):
    """Test that all error pages follow consistent design patterns"""
    error_routes = ["/test-403", "/test-404", "/test-500", "/test-429"]

    for route in error_routes:
        response = client.get(route)
        # Check consistent structure
        assert b'<section class="container text-center">' in response.data
        assert b'class="px-3 py-4 px-sm-4 py-sm-5"' in response.data
        assert b'class="lead bg-text-primary"' in response.data
        # Check for home link
        assert b'href="' in response.data
        assert b'class="btn btn-primary"' in response.data

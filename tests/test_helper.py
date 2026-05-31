import json
import os
from unittest.mock import patch

from app import create_app
from cache import cache

from tests.fake_credentials import TEST_SECRET_KEY


def load_mock_data(file_name):
    """Load mock data from a JSON file located in the mock_data directory."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "mock_data", file_name)
    with open(file_path, "r") as file:
        return json.load(file)


def get_test_client():
    """Get a test client with test configuration."""
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": TEST_SECRET_KEY,
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
        "SQLALCHEMY_BINDS": {},
    }
    app = create_app(test_config)
    return app.test_client()


def clear_cache():
    cache.clear()


def mock_http_get(mock_response):
    return patch("requests.get", return_value=mock_response)


def assert_json_response(response, expected_status=200):
    assert response.status_code == expected_status
    assert response.is_json


def assert_response_status(response, expected_status=200):
    assert response.status_code == expected_status

import json
from unittest.mock import patch

from app import create_app
from cache import cache


def load_mock_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def get_test_client():
    # Initialize the app using the factory function
    app = create_app({
        'TESTING': True,
        'DEBUG_PRINT_ROUTES': False  # Explicitly set this to avoid KeyError
    })
    return app.test_client()


def clear_cache():
    cache.clear()


def mock_http_get(mock_response):
    return patch('requests.get', return_value=mock_response)


def assert_json_response(response, expected_status=200):
    assert response.status_code == expected_status
    assert response.is_json


def assert_response_status(response, expected_status=200):
    assert response.status_code == expected_status

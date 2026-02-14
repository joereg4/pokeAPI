from unittest.mock import patch

import pytest

from utils import get_cache_stats, warm_common_endpoints
from tests.test_helper import get_test_client, load_mock_data, assert_response_status
from app import create_app
from models.model import db


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


def test_static_resources_integration(client):
    """Test that CSS and JS files are properly linked in the HTML."""
    response = client.get("/")  # or any other route that includes the base template

    # Assert that the response status is OK
    assert response.status_code == 200

    # Check for CSS file link
    assert b'<link rel="stylesheet" href="/static/css/styles.css">' in response.data

    # Check for JavaScript file link (search.js is loaded by search.html partial)
    assert b'<script src="/static/js/search.js"></script>' in response.data

    # Optionally, check for Bootstrap or other resources if needed
    assert b'<link rel="stylesheet" href="/static/css/bootstrap.css">' in response.data
    assert (
        b'<script src="/static/vendor/jquery/jquery-3.7.1.js"></script>'
        in response.data
    )


def test_no_static_resources_js_in_head(client):
    """Verify that base.html no longer loads the static resources.js file.

    Search is now powered by the /api/search endpoint, so the old static
    resources.js (which shipped the full resource list to the client) is
    no longer included in the <head>.
    """
    response = client.get("/")
    assert response.status_code == 200
    # The old static script tag should NOT be present
    assert b'js/resources.js"></script>' not in response.data

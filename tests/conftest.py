"""
Shared test fixtures for the entire test suite.

All test files should use these fixtures instead of defining their own.
This ensures consistent test configuration and avoids duplicate setup code.
"""

import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from models.model import db, User
from flask_login import login_user

# Add the tests directory to the Python path so test helpers can be imported
test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)

# Path to mock_data directory (relative to project root, not tests/)
MOCK_DATA_DIR = os.path.join(os.path.dirname(test_dir), "mock_data")


# ---------------------------------------------------------------------------
# Helpers (not fixtures -- plain functions available via import)
# ---------------------------------------------------------------------------

def is_sqlite_url(url):
    """Check if the database URL is for SQLite."""
    return "sqlite" in str(url).lower()


def load_mock_data(file_name):
    """Load mock data from a JSON file in the mock_data directory.

    Usage:
        data = load_mock_data("bulbasaur_species.json")
    """
    file_path = os.path.join(MOCK_DATA_DIR, file_name)
    with open(file_path, "r") as f:
        return json.load(f)


def assert_response_status(response, expected_status=200):
    """Assert that a response has the expected HTTP status code."""
    assert response.status_code == expected_status


def assert_json_response(response, expected_status=200):
    """Assert that a response is JSON with the expected status code."""
    assert response.status_code == expected_status
    assert response.is_json


# ---------------------------------------------------------------------------
# Core app fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def app():
    """Create and configure a test Flask application instance.

    Forces SQLite in-memory database to prevent any accidental writes to
    production. Initializes cache (SimpleCache) and disables rate limiting.
    """
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_BINDS": {},
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 300,
    }

    # Patch the cache config BEFORE create_app so the Redis backend is never
    # initialized.  This prevents stale Redis entries from leaking into tests.
    simple_cache_config = {
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 0,
    }

    with patch.dict("os.environ", {"DATABASE_URL": "sqlite:///:memory:"}), \
         patch("cache.get_cache_config", return_value=simple_cache_config):
        app = create_app(test_config)

        with app.app_context():
            # Safety check: never allow tests to touch a real database
            if not is_sqlite_url(db.engine.url):
                raise RuntimeError(
                    "Test attempted to connect to non-SQLite database! "
                    "This is a safety check to prevent tests from modifying production data."
                )

            import limiter as limiter_module
            limiter_module.limiter.enabled = False

            db.create_all()
            yield app

            db.session.remove()
            db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def admin_user(app):
    """Create an admin user for testing."""
    with app.app_context():
        if not is_sqlite_url(db.engine.url):
            raise RuntimeError(
                "Test attempted to connect to non-SQLite database! "
                "Safety check to prevent tests from modifying production data."
            )

        user = User(username="admin", email="admin@test.com", is_admin=True)
        user.set_password("admin123")
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.rollback()
        db.session.query(User).delete()
        db.session.commit()


@pytest.fixture(scope="function")
def regular_user(app):
    """Create a regular (non-admin) user for testing."""
    with app.app_context():
        if not is_sqlite_url(db.engine.url):
            raise RuntimeError(
                "Test attempted to connect to non-SQLite database! "
                "Safety check to prevent tests from modifying production data."
            )

        user = User(username="user", email="user@test.com", is_admin=False)
        user.set_password("user123")
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.rollback()
        db.session.query(User).delete()
        db.session.commit()


@pytest.fixture(scope="function")
def auth_client(client, admin_user, app):
    """Create an authenticated client with admin privileges."""
    with app.app_context():
        with app.test_request_context():
            login_user(admin_user)
            with client.session_transaction() as session:
                session["_user_id"] = str(admin_user.id)
                session["_fresh"] = True
            yield client


@pytest.fixture(scope="function")
def regular_auth_client(client, regular_user, app):
    """Create an authenticated client without admin privileges."""
    with app.app_context():
        with app.test_request_context():
            login_user(regular_user)
            with client.session_transaction() as session:
                session["_user_id"] = str(regular_user.id)
                session["_fresh"] = True
            yield client


# ---------------------------------------------------------------------------
# Auto-use mocks (applied to every test automatically)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_redis(mocker):
    """Mock Redis for all tests so no real Redis connection is needed."""
    mock = mocker.patch("pokedex.redis_client.redis_client")
    mock.ping.return_value = True
    mock.get.return_value = "test_value"
    mock.set.return_value = True

    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = [10, True, 100, True]
    mock.pipeline.return_value = mock_pipeline

    return mock


@pytest.fixture(autouse=True)
def mock_cache_stats(mocker):
    """Mock cache stats for all tests."""
    mock_stats = {
        "status": "connected",
        "hit_rate": 75.5,
        "used_memory_human": "1.5M",
        "connected_clients": 10,
        "total_connections_received": 100,
        "uptime_in_seconds": 3600,
    }
    mocker.patch("routes.health.get_cache_stats", return_value=mock_stats)
    return mock_stats


# ---------------------------------------------------------------------------
# API mocking fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_api(mocker):
    """Mock pokedex.APIResource.fetch_data with a dispatcher.

    Register mock responses, and any unregistered lookup raises ValueError
    (mimicking a 404 from the real API).

    Usage in tests:
        def test_something(client, mock_api):
            mock_api.register("pokemon", "bulbasaur", {"name": "bulbasaur", "id": 1, ...})
            response = client.get("/pokemon/bulbasaur")
            assert response.status_code == 200
    """
    responses = {}

    def register(endpoint, id_or_name, data):
        """Register a mock response for a given endpoint + identifier."""
        responses[(endpoint, str(id_or_name).lower())] = data

    def fetch_side_effect(endpoint, id_or_name, **kwargs):
        key = (endpoint, str(id_or_name).lower())
        if key in responses:
            return responses[key]
        raise ValueError(f"{endpoint.replace('-', ' ').title()} '{id_or_name}' not found")

    mock = mocker.patch("pokedex.APIResource.fetch_data", side_effect=fetch_side_effect)
    mock.register = register
    mock.responses = responses
    return mock


@pytest.fixture
def mock_requests(mocker):
    """Mock requests.get for routes that make direct HTTP calls to PokéAPI.

    Returns a MagicMock that can be configured per-test. By default returns
    a 200 response with an empty JSON body.

    Usage in tests:
        def test_something(client, mock_requests):
            mock_requests.return_value.status_code = 200
            mock_requests.return_value.json.return_value = {"results": [], "count": 0}
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [], "count": 0}
    mock_response.raise_for_status.return_value = None

    mock = mocker.patch("requests.get", return_value=mock_response)
    return mock

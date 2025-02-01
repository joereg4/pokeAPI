import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from model import db, User
from flask_login import LoginManager, login_user

# Add the tests directory to the Python path
test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)


def is_sqlite_url(url):
    """Check if the database URL is for SQLite."""
    return "sqlite" in str(url).lower()


@pytest.fixture(autouse=True)
def disable_rate_limiter():
    """Disable rate limiting for all tests."""
    with patch("flask_limiter.extension.Limiter.exempt", return_value=True):
        yield


@pytest.fixture(scope="function")
def app():
    """Create and configure a test Flask application instance."""
    # Force SQLite for testing, regardless of environment settings
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # Force SQLite for tests
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_BINDS": {},
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 300,
    }

    # Ensure no environment variables can override the test database
    with patch.dict("os.environ", {"DATABASE_URL": "sqlite:///:memory:"}):
        app = create_app(test_config)

        # Create all tables in the test database
        with app.app_context():
            # Double check we're using SQLite before proceeding
            if not is_sqlite_url(db.engine.url):
                raise RuntimeError(
                    "Test attempted to connect to non-SQLite database! "
                    "This is a safety check to prevent tests from modifying production data."
                )

            # Initialize cache
            from cache import cache

            cache.init_app(app)

            db.create_all()
            yield app

            # Clean up
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


@pytest.fixture(scope="function")
def admin_user(app):
    """Create an admin user for testing."""
    with app.app_context():
        # Safety check - ensure we're using SQLite
        if not is_sqlite_url(db.engine.url):
            raise RuntimeError(
                "Test attempted to connect to non-SQLite database! "
                "This is a safety check to prevent tests from modifying production data."
            )

        user = User(username="admin", email="admin@test.com", is_admin=True)
        user.set_password("admin123")
        db.session.add(user)
        db.session.commit()
        yield user
        # Clean up - only if using SQLite
        db.session.rollback()
        db.session.query(User).delete()
        db.session.commit()


@pytest.fixture(scope="function")
def regular_user(app):
    """Create a regular user for testing."""
    with app.app_context():
        # Safety check - ensure we're using SQLite
        if not is_sqlite_url(db.engine.url):
            raise RuntimeError(
                "Test attempted to connect to non-SQLite database! "
                "This is a safety check to prevent tests from modifying production data."
            )

        user = User(username="user", email="user@test.com", is_admin=False)
        user.set_password("user123")
        db.session.add(user)
        db.session.commit()
        yield user
        # Clean up - only if using SQLite
        db.session.rollback()
        db.session.query(User).delete()
        db.session.commit()


@pytest.fixture(autouse=True)
def mock_redis(mocker):
    """Mock Redis for all tests."""
    mock = mocker.patch("pokedex.redis_client.redis_client")
    mock.ping.return_value = True
    mock.get.return_value = "test_value"
    mock.set.return_value = True

    # Mock pipeline operations
    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = [
        10,
        True,
        100,
        True,
    ]  # hourly_count, expire1, daily_count, expire2
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

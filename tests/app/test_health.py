import pytest
from flask import url_for
from tests.test_helper import get_test_client, assert_response_status
from utils import get_cache_stats, warm_common_endpoints
from bs4 import BeautifulSoup
from limiter import limiter
from app import create_app
from datetime import datetime, timedelta
from flask_limiter.errors import RateLimitExceeded
from flask_limiter.wrappers import Limit
from unittest.mock import MagicMock
import time


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def mock_rate_limiter(mocker):
    """Mock the rate limiter for tests."""
    mock_limiter = MagicMock()
    mock_limiter.current_limit.limit = 50  # Set to match the hourly limit
    mock_limiter.current_limit.remaining = 49  # Set remaining requests
    mock_limiter.current_limit.reset_at = int(time.time()) + 60  # Set reset time
    mocker.patch("routes.health.limiter", mock_limiter)
    return mock_limiter


@pytest.fixture
def mock_redis_stats(mocker):
    """Mock Redis stats for testing"""
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


@pytest.fixture
def mock_redis_cache(mocker):
    """Mock Redis cache for testing"""
    mock_cache = mocker.patch("routes.health.cache")
    mock_cache.set.return_value = True
    mock_cache.get.return_value = "ok"
    return mock_cache


def test_cache_health_endpoint_json(client, mock_rate_limiter, mock_redis_stats):
    """Test the JSON endpoint of the health check"""
    print("\n=== Testing JSON Health Endpoint ===")
    response = client.get("/health/cache/json")
    assert response.status_code == 200
    data = response.get_json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_cache_health_endpoint_html(
    client, mock_rate_limiter, mock_redis_stats, mock_redis_cache
):
    """Test the HTML view of the health check"""
    print("\n=== Testing HTML Health Endpoint ===")
    response = client.get("/health/cache")
    print(f"Response status: {response.status_code}")
    assert response.status_code == 200

    # Parse HTML response
    soup = BeautifulSoup(response.data, "html.parser")
    print(f"Page title: {soup.title.string}")

    # Check status badge
    status_badge = soup.find("span", class_="badge")
    print(f"Status badge: {status_badge.text if status_badge else 'Not found'}")
    assert status_badge is not None
    assert "operational" in status_badge.text.strip().lower()

    # Check for required sections
    required_sections = [
        "Cache Status",
        "Cache Statistics",
        "Rate Limits",
        "API Call Statistics",
    ]

    for section in required_sections:
        heading = soup.find("h4", string=lambda t: section in t if t else False)
        assert heading is not None, f"Missing section: {section}"
        print(f"Found section: {section}")

    # Check all sections have content
    cards = soup.find_all("div", class_="card-body")
    assert len(cards) >= len(required_sections), "Missing some content cards"

    # Verify each card has content
    for card in cards:
        heading = card.find("h4", class_="h5")
        assert heading is not None, "Card missing heading"
        content = card.find("p")
        assert content is not None, "Card missing content"
        print(f"Verified card: {heading.text.strip()}")


def test_cache_health_with_redis_failure(client, mock_rate_limiter, mocker):
    """Test health check when Redis is not responding"""
    print("\n=== Testing Redis Failure ===")

    # Mock Redis stats to simulate failure
    mock_failed_stats = {
        "status": "disconnected",
        "error": "Redis connection failed",
        "hit_rate": 0,
        "used_memory_human": "N/A",
        "connected_clients": 0,
        "total_connections_received": 0,
        "uptime_in_seconds": 0,
    }
    mocker.patch("routes.health.get_cache_stats", return_value=mock_failed_stats)

    # Mock Redis cache to simulate failure
    mock_cache = mocker.patch("routes.health.cache")
    mock_cache.set.side_effect = Exception("Redis connection failed")
    mock_cache.get.side_effect = Exception("Redis connection failed")

    # Test JSON endpoint
    print("Testing JSON endpoint...")
    response = client.get("/health/cache/json")
    assert response.status_code == 500
    data = response.get_json()
    assert data["status"] == "unhealthy"
    assert "Redis connection failed" in data["cache"]


def test_rate_limit_exceeded(client, mock_rate_limiter, mocker):
    """Test rate limit exceeded scenario"""
    print("\n=== Testing Rate Limit Exceeded ===")

    # Create a test route with a very strict rate limit
    def test_endpoint():
        return "OK"

    print(
        f"Original endpoint attributes: module={getattr(test_endpoint, '__module__', None)}, name={getattr(test_endpoint, '__name__', None)}, qualname={getattr(test_endpoint, '__qualname__', None)}"
    )

    # Add necessary attributes that Flask-Limiter expects
    test_endpoint.__module__ = "tests.app.test_health"
    test_endpoint.__name__ = "test_endpoint"
    test_endpoint.__qualname__ = "test_endpoint"

    print(
        f"Modified endpoint attributes: module={test_endpoint.__module__}, name={test_endpoint.__name__}, qualname={test_endpoint.__qualname__}"
    )

    # Create a wrapper function that preserves attributes and enforces rate limits
    def wrapper(f):
        def wrapped(*args, **kwargs):
            hit_count = mock_rate_limiter.limiter.get_hit_count.return_value
            if hit_count >= 1:  # Rate limit exceeded
                # Create a Limit object similar to the one in mock_rate_limiter fixture
                limit = mocker.MagicMock(spec=Limit)
                limit.amount = 1
                limit.__str__.return_value = "1 per minute"
                limit.error_message = "1 per minute"
                raise RateLimitExceeded(limit)
            return f(*args, **kwargs)

        # Copy attributes from the original function
        wrapped.__module__ = f.__module__
        wrapped.__name__ = f.__name__
        wrapped.__qualname__ = f.__qualname__
        return wrapped

    # Apply rate limit with our wrapper
    print("Applying rate limit decorator...")
    mock_rate_limiter.limit.return_value = wrapper
    limited_endpoint = mock_rate_limiter.limit("1/minute")(test_endpoint)

    print(
        f"Limited endpoint attributes: module={getattr(limited_endpoint, '__module__', None)}, name={getattr(limited_endpoint, '__name__', None)}, qualname={getattr(limited_endpoint, '__qualname__', None)}"
    )
    print(f"Limited endpoint type: {type(limited_endpoint)}")
    print(f"Limited endpoint dir: {dir(limited_endpoint)}")

    print("Registering test route with limit: 1/minute")
    client.application.add_url_rule(
        "/test-rate-limit", "test_rate_limit", limited_endpoint, methods=["GET"]
    )

    print("Route map:")
    for rule in client.application.url_map.iter_rules():
        print(f"  {rule.endpoint} -> {rule.rule} [{','.join(rule.methods)}]")

    # First request should succeed
    print("\nMaking first request...")
    mock_rate_limiter.limiter.get_hit_count.return_value = 0
    response = client.get("/test-rate-limit")
    print(f"First response status: {response.status_code}")
    assert response.status_code == 200

    # Second request should fail due to rate limit
    print("\nMaking second request (should be rate limited)...")
    mock_rate_limiter.limiter.get_hit_count.return_value = 1
    response = client.get("/test-rate-limit")
    print(f"Second response status: {response.status_code}")
    assert response.status_code == 429

    # Check if the error page title is present
    soup = BeautifulSoup(response.data, "html.parser")
    error_code = soup.find("h1")
    error_message = soup.find("p", class_="lead")
    print(f"Error page title: {error_code.text if error_code else 'Not found'}")
    print(f"Error message: {error_message.text if error_message else 'Not found'}")
    assert error_code and "429" in error_code.text
    assert error_message and "Rate Limit Exceeded" in error_message.text
    print("=== End Test ===\n")


def test_rate_limit_headers(client, mock_rate_limiter, mock_redis_stats):
    """Test rate limit headers in API responses"""
    print("\n=== Testing Rate Limit Headers ===")
    response = client.get("/health/cache/json")
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    assert response.status_code == 200

    # Check for rate limit headers
    headers = response.headers
    print(f"X-RateLimit-Limit: {headers.get('X-RateLimit-Limit')}")
    print(f"X-RateLimit-Remaining: {headers.get('X-RateLimit-Remaining')}")
    print(f"X-RateLimit-Reset: {headers.get('X-RateLimit-Reset')}")

    # Use the limits defined in limiter.py
    assert headers.get("X-RateLimit-Limit") == "50"  # Use the hourly limit
    assert headers.get("X-RateLimit-Remaining") == "49"  # Assuming one request was made
    assert "X-RateLimit-Reset" in headers
    print("=== End Test ===\n")

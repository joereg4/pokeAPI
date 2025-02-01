import pytest
from flask import url_for
from bs4 import BeautifulSoup
from datetime import datetime
from flask_limiter.errors import RateLimitExceeded
from flask_limiter.wrappers import Limit
from unittest.mock import MagicMock
import time
from unittest.mock import patch


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


def test_cache_health_endpoint_json(auth_client, mock_rate_limiter, mock_redis_stats):
    """Test the JSON endpoint of the health check"""
    print("\n=== Testing JSON Health Endpoint ===")
    response = auth_client.get("/health/cache/json")
    assert response.status_code == 200
    data = response.get_json()

    # Check response structure
    assert "status" in data
    assert "cache" in data
    assert "rate_limits" in data
    assert "api_calls" in data

    # Check values
    assert data["status"] == "healthy"
    assert data["cache"]["status"] == "connected"
    assert isinstance(data["cache"]["hit_rate"], float)
    assert isinstance(data["api_calls"]["hourly_calls"], int)
    assert isinstance(data["api_calls"]["daily_calls"], int)


def test_cache_health_endpoint_html(auth_client, mock_rate_limiter, mock_redis_stats):
    """Test the HTML view of the health check"""
    # Test successful case
    response = auth_client.get("/health/cache")
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, "html.parser")

    # Verify the page structure without making assumptions about specific styling
    assert "System Health" in soup.get_text()
    assert "Cache Status" in soup.get_text()
    assert "Cache Statistics" in soup.get_text()
    assert "Rate Limits" in soup.get_text()
    assert "API Call Statistics" in soup.get_text()

    # Test error case by simulating a cache failure
    with patch("cache.cache.set", side_effect=Exception("Cache error")):
        # Test HTML response
        response = auth_client.get("/health/cache")
        assert response.status_code == 500  # Should return 500 on error
        soup = BeautifulSoup(response.data, "html.parser")
        assert "error" in soup.get_text()  # Cache status should show error

        # Test JSON response
        response = auth_client.get(
            "/health/cache", headers={"Accept": "application/json"}
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data["status"] == "unhealthy"
        assert "Cache error" in data["cache"]


def test_cache_health_with_redis_failure(auth_client, mock_rate_limiter, mocker):
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

    # Test JSON endpoint
    print("Testing JSON endpoint...")
    response = auth_client.get("/health/cache/json")
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

    # Add necessary attributes that Flask-Limiter expects
    test_endpoint.__module__ = "tests.app.test_health"
    test_endpoint.__name__ = "test_endpoint"
    test_endpoint.__qualname__ = "test_endpoint"

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
    mock_rate_limiter.limit.return_value = wrapper
    limited_endpoint = mock_rate_limiter.limit("1/minute")(test_endpoint)

    # Register test route
    client.application.add_url_rule(
        "/test-rate-limit", "test_rate_limit", limited_endpoint, methods=["GET"]
    )

    # First request should succeed
    mock_rate_limiter.limiter.get_hit_count.return_value = 0
    response = client.get("/test-rate-limit")
    assert response.status_code == 200

    # Second request should fail due to rate limit
    mock_rate_limiter.limiter.get_hit_count.return_value = 1
    response = client.get("/test-rate-limit")
    assert response.status_code == 429

    # Check if the error page title is present
    soup = BeautifulSoup(response.data, "html.parser")
    error_code = soup.find("h1")
    error_message = soup.find("p", class_="lead")
    assert error_code and "429" in error_code.text
    assert error_message and "Rate Limit Exceeded" in error_message.text


def test_rate_limit_headers(auth_client, mock_rate_limiter, mock_redis_stats):
    """Test rate limit headers in API responses"""
    print("\n=== Testing Rate Limit Headers ===")
    response = auth_client.get("/health/cache/json")
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    assert response.status_code == 200

    # Check for rate limit headers
    headers = response.headers
    assert "X-RateLimit-Limit" in headers
    assert "X-RateLimit-Remaining" in headers
    assert "X-RateLimit-Reset" in headers

    # Verify header values
    assert headers["X-RateLimit-Limit"] == "50"
    assert headers["X-RateLimit-Remaining"] == "49"
    assert int(headers["X-RateLimit-Reset"]) > time.time()

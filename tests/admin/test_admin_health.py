import pytest
from unittest.mock import patch, MagicMock
import json
from flask import url_for


@patch("routes.health.redis_client")
@patch("utils.get_cache_stats")
@patch("routes.health.cache")
def test_health_check_success(mock_routes_cache, mock_stats, mock_redis, auth_client):
    """Test successful health check."""
    # Mock cache behavior
    mock_routes_cache.set.return_value = True
    mock_routes_cache.get.return_value = "ok"

    # Mock Redis stats
    mock_stats.return_value = {
        "status": "connected",
        "hit_rate": 75.5,
        "used_memory_human": "1.5M",
        "connected_clients": 10,
        "total_connections_received": 100,
        "uptime_in_seconds": 3600,
    }

    # Mock Redis pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = [
        10,
        None,
        100,
        None,
    ]  # hourly_calls, expire, daily_calls, expire
    mock_redis.pipeline.return_value = mock_pipeline

    # Mock Redis get for API stats
    mock_redis.get.side_effect = lambda key: (
        "10" if "hour" in key else "100" if "day" in key else None
    )

    response = auth_client.get("/health/cache", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["cache"] == "operational"
    assert "stats" in data
    assert "rate_limits" in data
    assert "api_calls" in data


def test_health_check_unauthorized(client):
    """Test health check requires authentication."""
    # Test HTML request - should redirect to login
    response = client.get("/health/cache")
    assert response.status_code == 302
    assert "/auth/login" in response.location

    # Test JSON request - should return 401
    response = client.get("/health/cache", headers={"Accept": "application/json"})
    assert response.status_code == 401
    assert response.is_json
    assert response.json["error"] == "Unauthorized"


@patch("routes.health.redis_client")
@patch("utils.get_cache_stats")
@patch("routes.health.cache")
def test_cache_health_success(mock_routes_cache, mock_stats, mock_redis, auth_client):
    """Test successful health check."""
    # Mock cache behavior
    mock_routes_cache.set.return_value = True
    mock_routes_cache.get.return_value = "ok"

    # Mock Redis stats
    mock_stats.return_value = {
        "status": "connected",
        "hit_rate": 75.5,
        "used_memory_human": "1.5M",
        "connected_clients": 10,
        "total_connections_received": 100,
        "uptime_in_seconds": 3600,
    }

    # Mock Redis pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = [
        10,
        None,
        100,
        None,
    ]  # hourly_calls, expire, daily_calls, expire
    mock_redis.pipeline.return_value = mock_pipeline

    # Mock Redis get for API stats
    mock_redis.get.side_effect = lambda key: (
        "10" if "hour" in key else "100" if "day" in key else None
    )

    response = auth_client.get("/health/cache", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["cache"] == "operational"
    assert "stats" in data
    assert "rate_limits" in data
    assert "api_calls" in data

    # Also test the HTML output for the new headings
    response_html = auth_client.get("/health/cache")
    assert b"System Status" in response_html.data
    assert b"Cache Statistics" in response_html.data


@patch("routes.health.redis_client")
@patch("utils.get_cache_stats")
@patch("routes.health.cache")
def test_cache_health_failure(mock_routes_cache, mock_stats, mock_redis, auth_client):
    """Test cache health check when Redis is down."""
    # Mock cache failure
    mock_routes_cache.set.side_effect = Exception("Redis connection failed")
    mock_routes_cache.get.side_effect = Exception("Redis connection failed")

    # Mock Redis failure stats
    mock_stats.return_value = {
        "status": "disconnected",
        "error": "Redis connection failed",
        "hit_rate": 0,
        "used_memory_human": "N/A",
        "connected_clients": 0,
        "total_connections_received": 0,
        "uptime_in_seconds": 0,
    }

    # Mock Redis client failure
    mock_redis.ping.side_effect = Exception("Redis connection failed")
    mock_redis.get.side_effect = Exception("Redis connection failed")

    response = auth_client.get("/health/cache", headers={"Accept": "application/json"})
    assert response.status_code == 500
    data = response.get_json()
    assert data["status"] == "unhealthy"
    assert "Redis connection failed" in data["cache"]


def test_cache_health_unauthorized(client):
    """Test cache health check requires authentication."""
    # Test HTML request - should redirect to login
    response = client.get("/health/cache")
    assert response.status_code == 302
    assert "/auth/login" in response.location

    # Test JSON request - should return 401
    response = client.get("/health/cache", headers={"Accept": "application/json"})
    assert response.status_code == 401
    assert response.is_json
    assert response.json["error"] == "Unauthorized"

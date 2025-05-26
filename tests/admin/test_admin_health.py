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
        [
            b"api_calls:endpoint:pokemon:hour:12345",
            b"api_calls:endpoint:move:hour:12345",
        ],  # keys
        [
            b"api_calls:resource:pokemon:1:hour:12345",
            b"api_calls:resource:pokemon:2:hour:12345",
            b"api_calls:resource:move:tackle:hour:12345",
        ],  # resource_keys
        [],  # method_keys
        b"10",  # hourly
        b"100",  # daily
    ]
    mock_redis.pipeline.return_value = mock_pipeline

    # Mock Redis keys for traffic stats
    mock_redis.keys.side_effect = lambda pattern: (
        [
            b"api_calls:endpoint:pokemon:hour:12345",
            b"api_calls:endpoint:move:hour:12345",
        ]
        if "endpoint" in pattern
        else (
            [
                b"api_calls:resource:pokemon:1:hour:12345",
                b"api_calls:resource:pokemon:2:hour:12345",
                b"api_calls:resource:move:tackle:hour:12345",
            ]
            if "resource" in pattern
            else []
        )
    )

    # Mock Redis get for API stats and traffic stats
    def get_side_effect(key):
        if isinstance(key, bytes):
            key = key.decode()
        if "pokedex:pokemon:1:name" in key:
            return b"Bulbasaur"
        if "pokedex:pokemon:2:name" in key:
            return b"Ivysaur"
        if "pokedex:move:tackle:name" in key:
            return b"Tackle"
        if key == "api_calls:endpoint:pokemon:hour:12345":
            return b"10"
        if key == "api_calls:endpoint:move:hour:12345":
            return b"5"
        if "hour" in key:
            return b"10"
        if "day" in key:
            return b"100"
        if "api_calls:resource:pokemon:1" in key:
            return b"7"
        if "api_calls:resource:pokemon:2" in key:
            return b"3"
        if "api_calls:resource:move:tackle" in key:
            return b"5"
        return None

    mock_redis.get.side_effect = get_side_effect
    mock_redis.mget.side_effect = lambda keys: [get_side_effect(k) for k in keys]

    response = auth_client.get("/health/cache", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["cache"] == "operational"
    assert "stats" in data
    assert "rate_limits" in data
    assert "traffic_stats" in data

    # Verify the new hierarchical structure
    traffic_stats = data["traffic_stats"]
    assert "endpoint_stats" in traffic_stats
    assert "pokemon" in traffic_stats["endpoint_stats"]
    assert "move" in traffic_stats["endpoint_stats"]

    # Check Pokemon endpoint data
    pokemon_stats = traffic_stats["endpoint_stats"]["pokemon"]
    assert pokemon_stats["total_calls"] == 10
    assert "resources" in pokemon_stats
    assert "Bulbasaur" in pokemon_stats["resources"]
    assert "Ivysaur" in pokemon_stats["resources"]

    # Check Move endpoint data
    move_stats = traffic_stats["endpoint_stats"]["move"]
    assert move_stats["total_calls"] == 5
    assert "resources" in move_stats
    assert "Tackle" in move_stats["resources"]

    # Check time period stats
    assert traffic_stats["hourly_calls"] == 10
    assert traffic_stats["daily_calls"] == 100
    assert traffic_stats["weekly_calls"] == 700
    assert traffic_stats["monthly_calls"] == 3000


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
    """Test successful health check with HTML response."""
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
        [b"api_calls:endpoint:pokemon:hour:12345"],  # keys
        [b"api_calls:resource:pokemon:1:hour:12345"],  # resource_keys
        [],  # method_keys
        b"10",  # hourly
        b"100",  # daily
    ]
    mock_redis.pipeline.return_value = mock_pipeline

    # Mock Redis keys and get for traffic stats
    mock_redis.keys.side_effect = lambda pattern: (
        [b"api_calls:endpoint:pokemon:hour:12345"]
        if "endpoint" in pattern
        else (
            [b"api_calls:resource:pokemon:1:hour:12345"]
            if "resource" in pattern
            else []
        )
    )

    def get_side_effect(key):
        if isinstance(key, bytes):
            key = key.decode()
        if "pokedex:pokemon:1:name" in key:
            return b"Bulbasaur"
        if "api_calls:resource:pokemon:1" in key:
            return b"7"
        if "api_calls:endpoint:pokemon" in key:
            return b"10"
        if "hour" in key:
            return b"10"
        if "day" in key:
            return b"100"
        if "week" in key:
            return b"50"
        if "month" in key:
            return b"200"
        return None

    mock_redis.get.side_effect = get_side_effect
    mock_redis.mget.side_effect = lambda keys: [get_side_effect(k) for k in keys]

    # Test HTML response
    response = auth_client.get("/health/cache")
    assert response.status_code == 200

    # Check for new HTML elements
    assert b"API Usage Statistics" in response.data
    assert b"Time Period Statistics" in response.data
    assert b"Endpoint" in response.data
    assert b"Total Calls" in response.data
    assert b"Rolling 7-Day Calls" in response.data
    assert b"Rolling 30-Day Calls" in response.data


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

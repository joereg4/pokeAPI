import pytest
from flask import url_for
from tests.test_helper import get_test_client, assert_response_status
from utils import get_cache_stats, warm_common_endpoints


@pytest.fixture
def client():
    return get_test_client()


def test_cache_health_endpoint(client):
    """Test the cache health check endpoint"""
    response = client.get("/health/cache")
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["cache"] == "operational"
    assert "stats" in data

    # Verify stats structure
    stats = data["stats"]
    assert "used_memory_human" in stats
    assert "connected_clients" in stats
    assert "hit_rate" in stats
    assert "total_connections_received" in stats
    assert "uptime_in_seconds" in stats


def test_cache_health_with_redis_failure(client, mocker):
    """Test health check when Redis is not responding"""
    # Mock Redis client to raise an exception
    mocker.patch(
        "flask_caching.backends.rediscache.RedisCache.get",
        side_effect=Exception("Redis connection failed"),
    )

    response = client.get("/health/cache")
    assert response.status_code == 500

    data = response.get_json()
    assert data["status"] == "unhealthy"
    assert "Redis connection failed" in data["cache"]

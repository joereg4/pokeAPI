"""Tests for Flask-Caching implementation"""

import pytest
from test_helper import get_test_client, assert_json_response, assert_response_status
from cache import cache
from utils import get_cache_stats, warm_common_endpoints


@pytest.fixture
def client():
    return get_test_client()


def test_route_caching(client):
    """Test that route responses are properly cached"""
    # First request - should hit the API
    response1 = client.get("/pokemon/1")
    assert_response_status(response1)

    # Second request - should come from cache
    response2 = client.get("/pokemon/1")
    assert_response_status(response2)

    # Both responses should be identical
    assert response1.data == response2.data


def test_cache_invalidation():
    """Test cache clearing functionality"""
    key = "test_key"
    cache.set(key, "test_value")
    assert cache.get(key) == "test_value"

    cache.delete(key)
    assert cache.get(key) is None


def test_cache_timeout():
    """Test that cached items expire properly"""
    import time

    key = "timeout_test"
    cache.set(key, "test_value", timeout=1)
    assert cache.get(key) == "test_value"

    time.sleep(1.1)  # Wait for cache to expire
    assert cache.get(key) is None

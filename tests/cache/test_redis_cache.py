"""Tests for Redis-specific caching functionality"""

import pytest
import json
from unittest.mock import patch
from pokedex.cache import save, load, redis_client
from pokedex.utils import Config


@pytest.fixture
def redis_mock():
    with patch("pokedex.cache.redis_client") as mock:
        yield mock


def test_redis_save_and_load(redis_mock):
    test_data = {"name": "Pikachu", "type": "Electric"}
    test_endpoint = "pokemon"
    test_resource_id = 25

    # Test save
    save(test_data, test_endpoint, test_resource_id)

    # Check if set was called with correct arguments
    redis_mock.set.assert_called_once()
    call_args = redis_mock.set.call_args
    assert call_args[0][0] == f"{test_endpoint}/{test_resource_id}/"
    assert json.loads(call_args[0][1].decode()) == test_data
    assert call_args[1]["ex"] == 7 * 24 * 60 * 60  # 7 days in seconds

    # Mock the get return value for load
    redis_mock.get.return_value = json.dumps(test_data).encode()

    # Test load
    loaded_data = load(test_endpoint, test_resource_id)
    assert loaded_data == test_data


def test_redis_connection_error(redis_mock):
    """Test handling of Redis connection errors"""
    redis_mock.set.side_effect = Exception("Connection error")

    # Should not raise exception, just log warning
    save({"test": "data"}, "pokemon", 1)

    # Verify set was attempted
    redis_mock.set.assert_called_once()

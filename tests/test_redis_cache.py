import pytest
import json
from unittest.mock import patch, MagicMock
from pokedex.cache import save, load, redis_client
from pokedex.utils import Config

@pytest.fixture
def redis_mock():
    with patch('pokedex.cache.redis_client') as mock:
        yield mock

@pytest.fixture
def mock_validate():
    with patch('pokedex.common.validate') as mock:
        yield mock

def test_save_and_load(redis_mock, mock_validate):
    test_data = {"name": "Pikachu", "type": "Electric"}
    test_endpoint = "pokemon"
    test_resource_id = 25  # Use an integer instead of a string

    # Test save
    save(test_data, test_endpoint, test_resource_id)

    # Check if set was called with correct arguments
    redis_mock.set.assert_called_once()
    call_args = redis_mock.set.call_args[0]
    assert call_args[0] == f"{test_endpoint}/{test_resource_id}/"  # Note the trailing slash
    assert json.loads(call_args[1]) == test_data

    # Check if expireat was called
    redis_mock.expireat.assert_called_once()

    # Mock the get return value for load
    redis_mock.get.return_value = json.dumps(test_data).encode()

    # Test load
    loaded_data = load(test_endpoint, test_resource_id)

    # Check if get was called with correct arguments
    redis_mock.get.assert_called_once_with(f"{test_endpoint}/{test_resource_id}/")  # Note the trailing slash

    # Check if loaded data matches the original data
    assert loaded_data == test_data

def test_load_missing_data(redis_mock, mock_validate):
    # Mock the get return value for non-existent data
    redis_mock.get.return_value = None

    # Test load with non-existent data
    with pytest.raises(KeyError):
        load("pokemon", 9999)  # Use an integer instead of a string

def test_save_invalid_data(mock_validate):
    # Test save with invalid data type
    with pytest.raises(ValueError):
        save("invalid data", "pokemon", 1)  # Use an integer instead of a string

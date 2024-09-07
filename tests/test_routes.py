import pytest

from tests.test_helper import get_test_client, assert_response_status


@pytest.fixture
def client():
    return get_test_client()


def test_index_route(client):
    response = client.get('/')
    assert_response_status(response)


def test_get_pokemon_detail_route(client):
    response = client.get('/pokemon/bulbasaur')
    assert_response_status(response)
    assert b"bulbasaur" in response.data

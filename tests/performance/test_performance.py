import pytest
import time
import requests
from pokedex.api import get_data, _session
from pokedex.common import api_url_build


def make_requests_without_session(pokemon_ids):
    times = []
    for pokemon_id in pokemon_ids:
        start = time.time()
        url = api_url_build("pokemon", pokemon_id)
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        assert "name" in data
        times.append(time.time() - start)
    return times


def make_requests_with_session(pokemon_ids):
    times = []
    for pokemon_id in pokemon_ids:
        start = time.time()
        url = api_url_build("pokemon", pokemon_id)
        response = _session.get(url)
        response.raise_for_status()
        data = response.json()
        assert "name" in data
        times.append(time.time() - start)
    return times


def test_connection_pooling_performance():
    pokemon_ids = range(1, 11)  # Test with first 10 Pokemon

    # Test without session (no connection pooling)
    times_without_session = make_requests_without_session(pokemon_ids)
    avg_time_without_session = sum(times_without_session) / len(times_without_session)

    # Test with session (connection pooling)
    times_with_session = make_requests_with_session(pokemon_ids)
    avg_time_with_session = sum(times_with_session) / len(times_with_session)

    print(
        f"\nAverage request time WITHOUT connection pooling: {avg_time_without_session:.3f} seconds"
    )
    print(
        f"Average request time WITH connection pooling: {avg_time_with_session:.3f} seconds"
    )
    print(
        f"Performance improvement: {((avg_time_without_session - avg_time_with_session) / avg_time_without_session * 100):.1f}%"
    )

    # Assert that connection pooling is faster
    assert (
        avg_time_with_session < avg_time_without_session
    ), "Connection pooling should improve performance"

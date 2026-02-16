"""
Performance tests for connection pooling.

These tests hit the real PokéAPI to measure connection pooling benefits.
They are marked as integration tests and are skipped in CI by default.

Run manually:
    pytest tests/performance/ -m integration --timeout=60
"""

import pytest
import time
import requests
from pokedex.api import _session
from pokedex.common import api_url_build

pytestmark = pytest.mark.integration


def make_requests_without_session(pokemon_ids):
    """Make requests without connection pooling (new connection each time)."""
    times = []
    for pokemon_id in pokemon_ids:
        start = time.time()
        url = api_url_build("pokemon", pokemon_id)
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        assert "name" in data
        times.append(time.time() - start)
    return times


def make_requests_with_session(pokemon_ids):
    """Make requests with connection pooling via the shared session."""
    times = []
    for pokemon_id in pokemon_ids:
        start = time.time()
        url = api_url_build("pokemon", pokemon_id)
        response = _session.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        assert "name" in data
        times.append(time.time() - start)
    return times


def test_connection_pooling_performance():
    """Verify that connection pooling is at least not significantly slower.

    Due to network variability, we use a generous tolerance.
    The main goal is to confirm pooling isn't broken, not to
    measure exact speedup.
    """
    pokemon_ids = range(1, 11)  # First 10 Pokemon

    times_without = make_requests_without_session(pokemon_ids)
    avg_without = sum(times_without) / len(times_without)

    times_with = make_requests_with_session(pokemon_ids)
    avg_with = sum(times_with) / len(times_with)

    print(f"\nAverage WITHOUT pooling: {avg_without:.3f}s")
    print(f"Average WITH pooling:    {avg_with:.3f}s")

    improvement = (avg_without - avg_with) / avg_without * 100
    print(f"Improvement: {improvement:.1f}%")

    # Allow 10ms tolerance for network variability
    tolerance = 0.01
    assert avg_with < avg_without + tolerance, (
        f"Connection pooling is significantly slower: "
        f"{avg_with:.3f}s vs {avg_without:.3f}s"
    )

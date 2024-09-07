import shelve

from pytest import fixture, raises

from pokedex import cache


# Define a fixture to reset the cache directory and clear the shelve-based cache before each test
@fixture
def clear_cache(request):
    """Fixture to clear the shelve-based cache before and after each test."""
    # Reset cache to the default location
    cache.set_cache()

    # Clear the shelve-based cache before the test
    with shelve.open(cache.API_CACHE) as shelf:
        shelf.clear()

    # Define a finalizer to clear the cache after the test
    def clear_after_test():
        with shelve.open(cache.API_CACHE) as shelf:
            shelf.clear()

    # Register the finalizer to run after the test
    request.addfinalizer(clear_after_test)


def test_cache_functionality(clear_cache):
    """Test that Pokémon data is cached and retrieved properly."""

    # Mock the function that fetches data from the API
    data_to_cache = {"name": "bulbasaur", "id": 1}

    # Debugging: Check cache path
    print(f"API_CACHE path: {cache.API_CACHE}")

    # Save data to cache using an integer for resource_id
    cache.save(data_to_cache, "pokemon", 1)  # Pass Pokémon ID as an integer (1)

    # Load data from cache and verify it's the same
    cached_data = cache.load("pokemon", 1)  # Load by ID
    assert cached_data == data_to_cache  # Check that cached data matches

    # Attempt to load non-existent cache and verify it raises KeyError
    with raises(KeyError):
        cache.load("pokemon", 9999)  # Non-existent ID

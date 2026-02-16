# tests/pokedex/test_species_resolver.py
"""Unit tests for pokedex.species_resolver.

Tests cover:
  - Name passthrough (non-numeric IDs)
  - Low IDs (<10000) returned as-is
  - Form IDs (>=10000) resolved via API and cached in Redis
  - Redis cache hits avoid API calls
  - Graceful fallback when API or Redis fails
  - resolve_species_id_from_data() with pokemon dicts
  - warm_cache() for batch pre-warming
"""

import pytest
from unittest.mock import patch, MagicMock


class TestResolveSpeciesId:
    """Tests for resolve_species_id() — the main public function."""

    def test_name_passthrough(self):
        """String names (non-numeric) pass through unchanged."""
        from pokedex.species_resolver import resolve_species_id
        assert resolve_species_id("pikachu") == "pikachu"

    def test_none_passthrough(self):
        """None passes through unchanged."""
        from pokedex.species_resolver import resolve_species_id
        assert resolve_species_id(None) is None

    def test_low_id_returned_as_is(self):
        """IDs below 10000 are already species IDs."""
        from pokedex.species_resolver import resolve_species_id
        assert resolve_species_id(25) == 25
        assert resolve_species_id(9999) == 9999

    def test_string_low_id_converted(self):
        """Numeric strings below 10000 are converted to int and returned."""
        from pokedex.species_resolver import resolve_species_id
        assert resolve_species_id("25") == 25

    @patch("pokedex.species_resolver.redis_client")
    @patch("pokedex.species_resolver._fetch_species_id")
    def test_form_id_cache_miss_fetches_api(self, mock_fetch, mock_redis):
        """Form IDs (>=10000) not in cache trigger an API fetch."""
        from pokedex.species_resolver import resolve_species_id

        mock_redis.get.return_value = None  # Cache miss
        mock_fetch.return_value = 386  # Deoxys species ID

        result = resolve_species_id(10001)

        assert result == 386
        mock_fetch.assert_called_once_with(10001)
        mock_redis.set.assert_called_once_with("species_id:10001", "386", ex=2592000)

    @patch("pokedex.species_resolver.redis_client")
    @patch("pokedex.species_resolver._fetch_species_id")
    def test_form_id_cache_hit_skips_api(self, mock_fetch, mock_redis):
        """Form IDs found in Redis skip the API call."""
        from pokedex.species_resolver import resolve_species_id

        mock_redis.get.return_value = "386"  # Cache hit

        result = resolve_species_id(10001)

        assert result == 386
        mock_fetch.assert_not_called()

    @patch("pokedex.species_resolver.redis_client")
    @patch("pokedex.species_resolver._fetch_species_id")
    def test_form_id_api_failure_returns_original(self, mock_fetch, mock_redis):
        """If API fails to resolve, the original ID is returned."""
        from pokedex.species_resolver import resolve_species_id

        mock_redis.get.return_value = None
        mock_fetch.return_value = None  # Resolution failed

        result = resolve_species_id(10001)

        assert result == 10001

    @patch("pokedex.species_resolver.redis_client")
    @patch("pokedex.species_resolver._fetch_species_id")
    def test_redis_read_failure_still_fetches(self, mock_fetch, mock_redis):
        """Redis failure doesn't prevent API resolution."""
        from pokedex.species_resolver import resolve_species_id

        mock_redis.get.side_effect = Exception("Redis down")
        mock_fetch.return_value = 386

        result = resolve_species_id(10001)

        assert result == 386

    @patch("pokedex.species_resolver.redis_client")
    @patch("pokedex.species_resolver._fetch_species_id")
    def test_redis_write_failure_still_returns(self, mock_fetch, mock_redis):
        """Redis write failure doesn't prevent returning the result."""
        from pokedex.species_resolver import resolve_species_id

        mock_redis.get.return_value = None
        mock_fetch.return_value = 386
        mock_redis.set.side_effect = Exception("Redis down")

        result = resolve_species_id(10001)

        assert result == 386


class TestResolveSpeciesIdFromData:
    """Tests for resolve_species_id_from_data() — dict-based resolver."""

    @patch("pokedex.species_resolver.redis_client")
    def test_extracts_from_species_url(self, mock_redis):
        """Species URL in pokemon dict is correctly parsed."""
        from pokedex.species_resolver import resolve_species_id_from_data

        pokemon = {
            "id": 10001,
            "species": {"url": "https://pokeapi.co/api/v2/pokemon-species/386/"},
        }

        result = resolve_species_id_from_data(pokemon)

        assert result == 386
        # Should cache since it's a form ID
        mock_redis.set.assert_called_once()

    @patch("pokedex.species_resolver.redis_client")
    def test_low_id_not_cached(self, mock_redis):
        """Low IDs resolved from data are not redundantly cached."""
        from pokedex.species_resolver import resolve_species_id_from_data

        pokemon = {
            "id": 25,
            "species": {"url": "https://pokeapi.co/api/v2/pokemon-species/25/"},
        }

        result = resolve_species_id_from_data(pokemon)

        assert result == 25
        mock_redis.set.assert_not_called()

    def test_no_species_url_falls_back_to_id(self):
        """Missing species URL falls back to pokemon's own ID."""
        from pokedex.species_resolver import resolve_species_id_from_data

        pokemon = {"id": 10001, "species": {}}

        result = resolve_species_id_from_data(pokemon)

        assert result == 10001

    def test_none_species_falls_back(self):
        """None species falls back to pokemon's own ID."""
        from pokedex.species_resolver import resolve_species_id_from_data

        pokemon = {"id": 25, "species": None}

        result = resolve_species_id_from_data(pokemon)

        assert result == 25


class TestFetchSpeciesId:
    """Tests for _fetch_species_id() — the API call helper."""

    @patch("pokedex.interface.APIResource.fetch_data")
    def test_successful_fetch(self, mock_fetch):
        """Successfully fetches and extracts species ID from API."""
        from pokedex.species_resolver import _fetch_species_id

        mock_fetch.return_value = {
            "id": 10001,
            "species": {"url": "https://pokeapi.co/api/v2/pokemon-species/386/"},
        }

        result = _fetch_species_id(10001)

        assert result == 386
        mock_fetch.assert_called_once_with("pokemon", 10001)

    @patch("pokedex.interface.APIResource.fetch_data")
    def test_api_error_returns_none(self, mock_fetch):
        """API errors return None."""
        from pokedex.species_resolver import _fetch_species_id

        mock_fetch.side_effect = ValueError("Not found")

        result = _fetch_species_id(99999)

        assert result is None

    @patch("pokedex.interface.APIResource.fetch_data")
    def test_no_species_url_returns_none(self, mock_fetch):
        """Missing species URL in API response returns None."""
        from pokedex.species_resolver import _fetch_species_id

        mock_fetch.return_value = {"id": 10001, "species": {}}

        result = _fetch_species_id(10001)

        assert result is None


class TestWarmCache:
    """Tests for warm_cache() — batch pre-warming."""

    @patch("pokedex.species_resolver.resolve_species_id")
    def test_warms_multiple_ids(self, mock_resolve):
        """Resolves and returns mappings for all form IDs."""
        from pokedex.species_resolver import warm_cache

        mock_resolve.side_effect = lambda pid: {10001: 386, 10002: 386}[pid]

        result = warm_cache([10001, 10002])

        assert result == {10001: 386, 10002: 386}
        assert mock_resolve.call_count == 2

    @patch("pokedex.species_resolver.resolve_species_id")
    def test_skips_unresolved(self, mock_resolve):
        """IDs that resolve to themselves are not included in results."""
        from pokedex.species_resolver import warm_cache

        mock_resolve.side_effect = lambda pid: pid  # No resolution

        result = warm_cache([10001])

        assert result == {}

    @patch("pokedex.species_resolver.resolve_species_id")
    def test_empty_input(self, mock_resolve):
        """Empty input returns empty dict."""
        from pokedex.species_resolver import warm_cache

        result = warm_cache([])

        assert result == {}
        mock_resolve.assert_not_called()

"""
Unit tests for pokedex.api module.

Tests caching behavior, HTTP calls, English data filtering,
and sprite fetching -- all with mocked I/O.
"""

import pytest
import json
import requests
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# get_data: cache hit / miss / force_lookup
# ---------------------------------------------------------------------------

class TestGetData:
    """Tests for pokedex.api.get_data (the main data-fetching entry point)."""

    def test_returns_cached_data_on_hit(self):
        """When the cache has data, get_data should return it without making HTTP calls."""
        cached = {"name": "bulbasaur", "id": 1}

        with patch("pokedex.api.load", return_value=cached) as mock_load, \
             patch("pokedex.api._call_api") as mock_call:
            from pokedex.api import get_data
            result = get_data("pokemon", 1)

        mock_load.assert_called_once_with("pokemon", 1, None)
        mock_call.assert_not_called()
        assert result == cached

    def test_fetches_from_api_on_cache_miss(self):
        """When cache raises KeyError, get_data should call the API and save the result."""
        api_data = {"name": "charmander", "id": 4}

        with patch("pokedex.api.load", side_effect=KeyError) as mock_load, \
             patch("pokedex.api._call_api", return_value=api_data) as mock_call, \
             patch("pokedex.api.save") as mock_save:
            from pokedex.api import get_data
            result = get_data("pokemon", 4)

        mock_load.assert_called_once()
        mock_call.assert_called_once_with("pokemon", 4, None)
        mock_save.assert_called_once_with(api_data, "pokemon", 4, None)
        assert result == api_data

    def test_force_lookup_skips_cache(self):
        """When force_lookup=True, the cache should be bypassed entirely."""
        api_data = {"name": "squirtle", "id": 7}

        with patch("pokedex.api.load") as mock_load, \
             patch("pokedex.api._call_api", return_value=api_data), \
             patch("pokedex.api.save"):
            from pokedex.api import get_data
            result = get_data("pokemon", 7, force_lookup=True)

        mock_load.assert_not_called()
        assert result == api_data


# ---------------------------------------------------------------------------
# filter_english_data
# ---------------------------------------------------------------------------

class TestFilterEnglishData:
    """Tests for pokedex.api.filter_english_data."""

    def test_filters_names_to_english_only(self):
        from pokedex.api import filter_english_data

        data = {
            "id": 1,
            "names": [
                {"name": "Bulbasaur", "language": {"name": "en"}},
                {"name": "Bisasam", "language": {"name": "de"}},
                {"name": "Fushigidane", "language": {"name": "ja"}},
            ],
        }
        result = filter_english_data(data)
        assert len(result["names"]) == 1
        assert result["names"][0]["name"] == "Bulbasaur"

    def test_filters_flavor_text_to_english(self):
        from pokedex.api import filter_english_data

        data = {
            "flavor_text_entries": [
                {"flavor_text": "A seed pokemon", "language": {"name": "en"}},
                {"flavor_text": "Ein Samen Pokemon", "language": {"name": "de"}},
            ],
        }
        result = filter_english_data(data)
        assert len(result["flavor_text_entries"]) == 1
        assert result["flavor_text_entries"][0]["language"]["name"] == "en"

    def test_leaves_non_list_fields_untouched(self):
        """Fields like 'color' or 'habitat' that are dicts (not lists) should pass through."""
        from pokedex.api import filter_english_data

        data = {
            "color": {"name": "green"},
            "habitat": {"name": "grassland"},
            "id": 1,
        }
        result = filter_english_data(data)
        assert result["color"] == {"name": "green"}
        assert result["id"] == 1

    def test_handles_missing_fields_gracefully(self):
        """Data without any filterable fields should pass through unchanged."""
        from pokedex.api import filter_english_data

        data = {"id": 25, "name": "pikachu", "height": 4}
        result = filter_english_data(data)
        assert result == data

    def test_does_not_mutate_original(self):
        """filter_english_data should return a copy, not modify the input."""
        from pokedex.api import filter_english_data

        data = {
            "names": [
                {"name": "Bulbasaur", "language": {"name": "en"}},
                {"name": "Bisasam", "language": {"name": "de"}},
            ]
        }
        original_len = len(data["names"])
        filter_english_data(data)
        assert len(data["names"]) == original_len


# ---------------------------------------------------------------------------
# get_sprite: cache / upstream / 404 handling
# ---------------------------------------------------------------------------

class TestGetSprite:
    """Tests for pokedex.api.get_sprite."""

    def test_returns_cached_sprite_on_hit(self):
        """When a sprite is cached on disk, return it without fetching upstream."""
        cached = {"img_data": b"png bytes", "path": "/cache/pokemon/1.png"}

        with patch("pokedex.api.load_sprite", return_value=cached) as mock_load, \
             patch("pokedex.api._call_sprite_api") as mock_call:
            from pokedex.api import get_sprite
            result = get_sprite("pokemon", 1)

        mock_load.assert_called_once()
        mock_call.assert_not_called()
        assert result == cached

    def test_fetches_upstream_on_cache_miss(self):
        """When the sprite file doesn't exist, fetch from upstream and cache it."""
        upstream = {"img_data": b"new png", "path": "/cache/pokemon/25.png"}

        with patch("pokedex.api.load_sprite", side_effect=FileNotFoundError), \
             patch("pokedex.api._call_sprite_api", return_value=upstream), \
             patch("pokedex.api.save_sprite") as mock_save:
            from pokedex.api import get_sprite
            result = get_sprite("pokemon", 25)

        mock_save.assert_called_once()
        assert result == upstream

    def test_returns_none_on_upstream_404(self):
        """When upstream returns 404, get_sprite should return None (not raise)."""
        with patch("pokedex.api.load_sprite", side_effect=FileNotFoundError), \
             patch("pokedex.api._call_sprite_api", return_value=None), \
             patch("pokedex.api.save_sprite") as mock_save:
            from pokedex.api import get_sprite
            result = get_sprite("pokemon", 99999)

        mock_save.assert_not_called()
        assert result is None

    def test_force_lookup_skips_cache(self):
        """force_lookup=True should bypass the file cache."""
        upstream = {"img_data": b"fresh", "path": "/cache/pokemon/1.png"}

        with patch("pokedex.api.load_sprite") as mock_load, \
             patch("pokedex.api._call_sprite_api", return_value=upstream), \
             patch("pokedex.api.save_sprite"):
            from pokedex.api import get_sprite
            result = get_sprite("pokemon", 1, force_lookup=True)

        mock_load.assert_not_called()
        assert result == upstream


# ---------------------------------------------------------------------------
# _call_sprite_api: 404 vs other errors
# ---------------------------------------------------------------------------

class TestCallSpriteApi:
    """Tests for pokedex.api._call_sprite_api."""

    def test_returns_none_on_404(self):
        """A 404 from upstream should return None, not raise."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.HTTPError(response=mock_response)

        with patch("pokedex.api._http_get", side_effect=http_error):
            from pokedex.api import _call_sprite_api
            result = _call_sprite_api("pokemon", 99999)

        assert result is None

    def test_raises_on_500(self):
        """A 500 from upstream should propagate as an exception."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = requests.HTTPError(response=mock_response)

        with patch("pokedex.api._http_get", side_effect=http_error):
            from pokedex.api import _call_sprite_api
            with pytest.raises(requests.HTTPError):
                _call_sprite_api("pokemon", 1)

    def test_returns_data_on_success(self):
        """A successful response should return img_data and path."""
        mock_response = MagicMock()
        mock_response.content = b"image bytes"

        with patch("pokedex.api._http_get", return_value=mock_response), \
             patch("pokedex.api.get_sprite_path", return_value="/cache/pokemon/1.png"):
            from pokedex.api import _call_sprite_api
            result = _call_sprite_api("pokemon", 1)

        assert result["img_data"] == b"image bytes"
        assert result["path"] == "/cache/pokemon/1.png"

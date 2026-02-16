"""Unit tests for the unified PokeAPIClient (pokedex/client.py).

These tests verify that the client correctly delegates to the underlying
api.py functions and adds the higher-level capabilities (pagination,
direct URL access, count fetching).
"""

import pytest
from unittest.mock import patch, MagicMock


class TestClientFetch:
    """Tests for client.fetch() -- single resource retrieval."""

    def test_fetch_delegates_to_get_data(self):
        """fetch() should call api.get_data with the correct arguments."""
        with patch("pokedex.client.get_data") as mock_get_data:
            mock_get_data.return_value = {"name": "pikachu", "id": 25}
            from pokedex.client import client

            result = client.fetch("pokemon", "pikachu")

            mock_get_data.assert_called_once_with(
                "pokemon", resource_id="pikachu", force_lookup=False
            )
            assert result["name"] == "pikachu"

    def test_fetch_with_force_refresh(self):
        """fetch(force_refresh=True) should pass force_lookup=True."""
        with patch("pokedex.client.get_data") as mock_get_data:
            mock_get_data.return_value = {"name": "pikachu", "id": 25}
            from pokedex.client import client

            client.fetch("pokemon", "pikachu", force_refresh=True)

            mock_get_data.assert_called_once_with(
                "pokemon", resource_id="pikachu", force_lookup=True
            )

    def test_fetch_without_id(self):
        """fetch() with no id_or_name should fetch the full endpoint list."""
        with patch("pokedex.client.get_data") as mock_get_data:
            mock_get_data.return_value = {"count": 1302, "results": []}
            from pokedex.client import client

            result = client.fetch("pokemon")

            mock_get_data.assert_called_once_with(
                "pokemon", resource_id=None, force_lookup=False
            )
            assert result["count"] == 1302


class TestClientFetchSprite:
    """Tests for client.fetch_sprite() -- sprite image retrieval."""

    def test_fetch_sprite_delegates_to_get_sprite(self):
        """fetch_sprite() should call api.get_sprite with correct args."""
        with patch("pokedex.client.get_sprite") as mock_get_sprite:
            mock_get_sprite.return_value = {"img_data": b"png", "path": "/tmp/test.png"}
            from pokedex.client import client

            result = client.fetch_sprite("pokemon", 25, other=True, official_artwork=True)

            mock_get_sprite.assert_called_once_with(
                "pokemon", 25, other=True, official_artwork=True
            )
            assert result["img_data"] == b"png"

    def test_fetch_sprite_returns_none_on_missing(self):
        """fetch_sprite() should return None when upstream returns 404."""
        with patch("pokedex.client.get_sprite") as mock_get_sprite:
            mock_get_sprite.return_value = None
            from pokedex.client import client

            result = client.fetch_sprite("pokemon", 99999)

            assert result is None


class TestClientFetchList:
    """Tests for client.fetch_list() -- paginated list retrieval."""

    def test_fetch_list_builds_url_and_params(self):
        """fetch_list() should call _http_get with the correct URL and params."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "count": 1302,
            "next": None,
            "results": [{"name": "bulbasaur"}],
        }
        with patch("pokedex.client._http_get", return_value=mock_response) as mock_get:
            from pokedex.client import client

            result = client.fetch_list("pokemon", limit=20, offset=40)

            # Verify _http_get was called with the built URL and params
            call_args = mock_get.call_args
            assert "pokemon" in call_args[0][0]  # URL contains endpoint
            assert call_args[1] == {"limit": 20, "offset": 40}
            assert result["count"] == 1302

    def test_fetch_list_without_params(self):
        """fetch_list() with no limit/offset should not pass params."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"count": 100, "results": []}
        with patch("pokedex.client._http_get", return_value=mock_response) as mock_get:
            from pokedex.client import client

            client.fetch_list("ability")

            call_args = mock_get.call_args
            assert call_args[1] == {}


class TestClientFetchCount:
    """Tests for client.fetch_count() -- endpoint count retrieval."""

    def test_fetch_count_returns_integer(self):
        """fetch_count() should return the count as an integer."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"count": 1302, "results": []}
        with patch("pokedex.client._http_get", return_value=mock_response):
            from pokedex.client import client

            count = client.fetch_count("pokemon")

            assert count == 1302
            assert isinstance(count, int)


class TestClientFetchUrl:
    """Tests for client.fetch_url() -- direct URL access."""

    def test_fetch_url_delegates_to_http_get(self):
        """fetch_url() should call _http_get with the given URL."""
        mock_response = MagicMock()
        with patch("pokedex.client._http_get", return_value=mock_response) as mock_get:
            from pokedex.client import client

            result = client.fetch_url("https://pokeapi.co/api/v2/pokemon/25")

            mock_get.assert_called_once_with("https://pokeapi.co/api/v2/pokemon/25")
            assert result is mock_response

    def test_fetch_url_json_returns_parsed_json(self):
        """fetch_url_json() should return parsed JSON from the response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "pikachu"}
        with patch("pokedex.client._http_get", return_value=mock_response):
            from pokedex.client import client

            result = client.fetch_url_json("https://pokeapi.co/api/v2/pokemon/25")

            assert result == {"name": "pikachu"}


class TestClientFetchAllPages:
    """Tests for client.fetch_all_pages() -- pagination follower."""

    def test_fetch_all_pages_follows_next_links(self):
        """fetch_all_pages() should follow 'next' links until None."""
        page1 = MagicMock()
        page1.json.return_value = {
            "results": [{"name": "bulbasaur"}, {"name": "ivysaur"}],
            "next": "https://pokeapi.co/api/v2/pokemon?offset=2&limit=2",
        }
        page2 = MagicMock()
        page2.json.return_value = {
            "results": [{"name": "venusaur"}],
            "next": None,
        }
        with patch("pokedex.client._http_get", side_effect=[page1, page2]):
            from pokedex.client import client

            results = client.fetch_all_pages("https://pokeapi.co/api/v2/pokemon?limit=2")

            assert len(results) == 3
            assert results[0]["name"] == "bulbasaur"
            assert results[2]["name"] == "venusaur"

    def test_fetch_all_pages_handles_single_page(self):
        """fetch_all_pages() should work when there's only one page."""
        page1 = MagicMock()
        page1.json.return_value = {
            "results": [{"name": "bulbasaur"}],
            "next": None,
        }
        with patch("pokedex.client._http_get", side_effect=[page1]):
            from pokedex.client import client

            results = client.fetch_all_pages("https://pokeapi.co/api/v2/pokemon?limit=1")

            assert len(results) == 1


class TestClientSingleton:
    """Tests for the module-level singleton."""

    def test_singleton_is_pokeapi_client_instance(self):
        """The module-level 'client' should be a PokeAPIClient instance."""
        from pokedex.client import client, PokeAPIClient

        assert isinstance(client, PokeAPIClient)

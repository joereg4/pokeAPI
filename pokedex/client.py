# client.py
# -*- coding: utf-8 -*-
"""Unified client for all PokéAPI communication.

This module provides a single, clean interface for fetching data from PokéAPI.
It wraps the existing api.py functions (which handle caching, connection pooling,
and HTTP error handling) and adds higher-level capabilities like paginated list
fetching and direct URL access.

Design rationale:
  - Delegates to api.get_data(), api.get_sprite(), and api._http_get() rather
    than reimplementing HTTP or caching logic.
  - Replaces scattered requests.get() calls across routes/ and pokedex/ with a
    consistent interface that uses the shared session and timeout config.
  - Does NOT replace APIResource, loaders.py, or interface.py -- those continue
    to work as-is and internally use the same api.py layer.

Usage:
    from pokedex.client import client

    data = client.fetch("pokemon", "pikachu")
    sprite = client.fetch_sprite("pokemon", 25, other=True, official_artwork=True)
    moves = client.fetch_list("move", limit=20, offset=0)
    count = client.fetch_count("pokemon")
    response = client.fetch_url("https://pokeapi.co/api/v2/pokemon/25")
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Union

import requests

from .api import SpriteData, _http_get, get_data, get_sprite
from .common import api_url_build

logger = logging.getLogger(__name__)


class PokeAPIClient:
    """Single source of truth for all PokéAPI communication.

    Methods:
        fetch         -- Fetch a single resource by endpoint and id/name (cached).
        fetch_sprite  -- Fetch sprite image data (cached on filesystem).
        fetch_list    -- Fetch a paginated list from any endpoint.
        fetch_count   -- Fetch just the resource count for an endpoint.
        fetch_url     -- Fetch any URL using the shared session + timeout.
        fetch_url_json -- Fetch a URL and return parsed JSON.
        fetch_all_pages -- Follow pagination links to collect all results.
    """

    # -- Single resource --------------------------------------------------

    def fetch(
        self,
        endpoint: str,
        id_or_name: Optional[Union[int, str]] = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Fetch a single API resource by endpoint and identifier.

        Equivalent to ``APIResource.fetch_data()`` but without the OOP wrapper.
        Results are cached in Redis via the existing cache layer.

        Args:
            endpoint: PokéAPI endpoint name (e.g. "pokemon", "ability").
            id_or_name: Resource identifier. None fetches the full list.
            force_refresh: Bypass cache and fetch fresh data from the API.

        Returns:
            Parsed JSON dict with English-filtered text fields.

        Raises:
            requests.HTTPError: On non-200 responses from upstream.
            ValueError: If the endpoint or id is invalid.
        """
        return get_data(
            endpoint,
            resource_id=id_or_name,
            force_lookup=force_refresh,
        )

    # -- Sprites -----------------------------------------------------------

    def fetch_sprite(
        self, sprite_type: str, sprite_id: Union[int, str], **kwargs: Any
    ) -> Optional[SpriteData]:
        """Fetch sprite image data for a Pokemon or other resource.

        Returns a dict with ``img_data`` (bytes) and ``path`` (str) on success,
        or None if the sprite does not exist upstream (404).

        Args:
            sprite_type: Resource type (e.g. "pokemon").
            sprite_id: Resource identifier.
            **kwargs: Sprite options (other, official_artwork, dream_world, etc.).

        Returns:
            Dict with img_data/path, or None if not found.
        """
        return get_sprite(sprite_type, sprite_id, **kwargs)

    # -- Paginated lists ---------------------------------------------------

    def fetch_list(
        self,
        endpoint: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> dict[str, Any]:
        """Fetch a paginated list from the API.

        This is the capability that was missing from the original api.py layer.
        Routes previously made direct requests.get() calls for paginated data;
        this method consolidates that pattern.

        Args:
            endpoint: PokéAPI endpoint name (e.g. "pokemon", "move").
            limit: Maximum number of results to return.
            offset: Number of results to skip from the beginning.

        Returns:
            Dict with "count", "next", "previous", and "results" keys.
        """
        url = api_url_build(endpoint)
        params: dict[str, int] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = _http_get(url, **params)
        return response.json()

    def fetch_count(self, endpoint: str) -> int:
        """Fetch just the total count for an endpoint.

        Lightweight call that requests only 1 result to minimize payload.

        Args:
            endpoint: PokéAPI endpoint name.

        Returns:
            Total number of resources in this endpoint.
        """
        url = api_url_build(endpoint)
        response = _http_get(url, limit=1)
        data = response.json()
        return data.get("count", 0)

    # -- Direct URL access -------------------------------------------------

    def fetch_url(self, url: str, **params: Any) -> requests.Response:
        """Fetch any URL using the shared HTTP session.

        Replaces direct requests.get() calls scattered across routes and
        summary generators. Uses the same connection pool, timeout, and error
        handling as the core API client.

        Args:
            url: Full URL to fetch.
            **params: Optional query parameters.

        Returns:
            requests.Response object.

        Raises:
            requests.HTTPError: On non-200 responses.
        """
        return _http_get(url, **params)

    def fetch_url_json(self, url: str, **params: Any) -> dict[str, Any]:
        """Fetch a URL and return parsed JSON.

        Convenience wrapper around fetch_url() for the common case
        where the response is JSON.

        Args:
            url: Full URL to fetch.
            **params: Optional query parameters.

        Returns:
            Parsed JSON dict.
        """
        response = self.fetch_url(url, **params)
        return response.json()

    # -- Pagination helpers ------------------------------------------------

    def fetch_all_pages(self, url: str) -> list[dict[str, Any]]:
        """Follow pagination links to collect all results.

        Replaces pokedex.helper.fetch_all_results() and similar patterns
        that manually followed "next" links.

        Args:
            url: Initial URL (with or without limit/offset params).

        Returns:
            List of all result dicts across all pages.
        """
        all_results: list[dict[str, Any]] = []
        current_url: Optional[str] = url
        while current_url:
            response = _http_get(current_url)
            data = response.json()
            all_results.extend(data.get("results", []))
            current_url = data.get("next")
        return all_results


# Module-level singleton -- import this rather than creating new instances.
# All methods are stateless (they delegate to the shared session in api.py),
# so a single instance is safe for concurrent use.
client = PokeAPIClient()

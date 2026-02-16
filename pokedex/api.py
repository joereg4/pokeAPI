from __future__ import annotations

import logging
from typing import Any, Optional, Union

import requests

from .cache import get_sprite_path, load, load_sprite, save, save_sprite
from .common import api_url_build, sprite_url_build

logger = logging.getLogger(__name__)

# Type alias for the sprite data dict returned by get_sprite / _call_sprite_api.
SpriteData = dict[str, Any]  # {"img_data": bytes, "path": str}

# Create a session object for connection pooling
_session = requests.Session()
_session.mount(
    "http://", requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
)
_session.mount(
    "https://", requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
)


def _http_get(url: str, **params: Any) -> requests.Response:
    """Execute an HTTP GET using the shared session with configured timeout."""
    from .utils import Config
    response = _session.get(url, params=params, timeout=Config.HTTP_TIMEOUT)
    response.raise_for_status()
    return response


def _call_api(
    endpoint: str,
    resource_id: Optional[Union[int, str]] = None,
    subresource: Optional[str] = None,
) -> dict[str, Any]:
    """Fetch and filter API data for an endpoint, auto-paginating full lists."""
    url = api_url_build(endpoint, resource_id, subresource)
    get_endpoint_list = resource_id is None
    response = _http_get(url)

    data = filter_english_data(response.json())

    if get_endpoint_list and data["count"] != len(data["results"]):
        items = data["count"]
        response = _http_get(url, limit=items)
        data = response.json()
    return data


def get_data(
    endpoint: str,
    resource_id: Optional[Union[int, str]] = None,
    subresource: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch resource data with Redis caching.

    Checks the cache first; on miss, fetches from the API and stores the result.

    Args:
        endpoint: PokéAPI endpoint name.
        resource_id: Resource identifier (int ID or string name).
        subresource: Optional subresource path.
        **kwargs: Pass ``force_lookup=True`` to bypass the cache.

    Returns:
        Parsed JSON dict (English-filtered for text fields).
    """
    force_lookup: bool = kwargs.get("force_lookup", False)

    if not force_lookup:
        try:
            return load(endpoint, resource_id, subresource)
        except KeyError:
            pass
    data = _call_api(endpoint, resource_id, subresource)
    save(data, endpoint, resource_id, subresource)
    return data


def _call_sprite_api(
    sprite_type: str, sprite_id: Union[int, str], **kwargs: Any
) -> Optional[SpriteData]:
    """Fetch sprite bytes from upstream. Return None on 404 to allow graceful fallbacks."""
    url = sprite_url_build(sprite_type, sprite_id, **kwargs)
    try:
        response = _http_get(url)
    except requests.HTTPError as e:
        # Treat 404s as expected-missing assets, not errors
        if e.response is not None and e.response.status_code == 404:
            logger.warning(
                "Sprite not found upstream (404)",
                extra={
                    "sprite_type": sprite_type,
                    "sprite_id": sprite_id,
                    "url": url,
                    "options": kwargs,
                },
            )
            return None
        # Re-raise other HTTP errors
        raise

    abs_path = get_sprite_path(sprite_type, sprite_id, **kwargs)
    data: SpriteData = dict(img_data=response.content, path=abs_path)
    return data


def get_sprite(
    sprite_type: str, sprite_id: Union[int, str], **kwargs: Any
) -> Optional[SpriteData]:
    """Get sprite data for a resource.

    Returns None when the upstream asset is missing (404) so callers can
    serve a placeholder instead of raising an internal error.
    """
    force_lookup: bool = kwargs.get("force_lookup", False)

    if not force_lookup:
        try:
            return load_sprite(sprite_type, sprite_id, **kwargs)
        except FileNotFoundError:
            pass

    data = _call_sprite_api(sprite_type, sprite_id, **kwargs)
    if data is None:
        return None
    save_sprite(data, sprite_type, sprite_id, **kwargs)
    return data


def filter_english_data(data: dict[str, Any]) -> dict[str, Any]:
    """Filter multilingual list fields to English-only entries."""
    filtered_data = data.copy()
    fields_to_filter = [
        "names",
        "effect_entries",
        "flavor_text_entries",
        "color",
        "genera",
        "habitat",
        "shape",
        "descriptions",
        "version_group",
    ]
    for field in fields_to_filter:
        if field in filtered_data:
            entries = filtered_data[field]
            if isinstance(entries, list):
                filtered_entries = [
                    entry
                    for entry in entries
                    if isinstance(entry, dict)
                    and isinstance(entry.get("language", {}), dict)
                    and entry["language"].get("name") == "en"
                ]
                filtered_data[field] = filtered_entries
    return filtered_data

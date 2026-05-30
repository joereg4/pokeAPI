# cache.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional, Union

import redis

from .common import cache_uri_build, sprite_filepath_build
from .redis_client import redis_client

# Cache locations will be set at the end of this file.
CACHE_DIR: Optional[str] = None
API_CACHE: Optional[str] = None
SPRITE_CACHE: Optional[str] = None
CACHE_EXPIRATION_DAYS: int = 7

logger = logging.getLogger(__name__)


def save(
    data: Union[dict[str, Any], list[Any]],
    endpoint: str,
    resource_id: Optional[Union[int, str]] = None,
    subresource: Optional[str] = None,
) -> None:
    """Persist API response data to Redis with an expiration TTL."""
    if data == dict():  # No point in saving empty data.
        return None

    if not isinstance(data, (dict, list)):
        raise ValueError("Could not save non-dict data")

    uri = cache_uri_build(endpoint, resource_id, subresource)

    try:
        compressed_data = json.dumps(data).encode("utf-8")
        redis_client.set(
            uri,
            compressed_data,
            ex=CACHE_EXPIRATION_DAYS * 24 * 60 * 60,
        )
    except (redis.RedisError, Exception) as error:
        logging.warning(f"Redis error, skipping save: {error}")
        return None


def save_sprite(
    data: dict[str, Any], sprite_type: str, sprite_id: Union[int, str], **kwargs: Any
) -> None:
    """Write sprite image bytes to the filesystem cache."""
    abs_path: str = data["path"]

    dirs = abs_path.rpartition(os.path.sep)[0]
    safe_make_dirs(dirs)

    with open(abs_path, "wb") as img_file:
        img_file.write(data["img_data"])

    logger.debug(f"Sprite saved successfully: {os.path.exists(abs_path)}")


def load(
    endpoint: str,
    resource_id: Optional[Union[int, str]] = None,
    subresource: Optional[str] = None,
) -> dict[str, Any]:
    """Load cached API response data from Redis.

    Raises:
        KeyError: If the data is not in the cache or Redis is unreachable.
    """
    uri = cache_uri_build(endpoint, resource_id, subresource)

    try:
        data = redis_client.get(uri)
        if data is None:
            raise KeyError("Data not found in cache")
        return json.loads(data)
    except redis.RedisError as error:
        logging.warning(f"Redis error, skipping load: {error}")
        raise KeyError("Cache could not be accessed.")


def load_sprite(
    sprite_type: str, sprite_id: Union[int, str], **kwargs: Any
) -> dict[str, Any]:
    """Load cached sprite image from the filesystem.

    Raises:
        FileNotFoundError: If the sprite has not been cached yet.
    """
    abs_path = get_sprite_path(sprite_type, sprite_id, **kwargs)

    with open(abs_path, "rb") as img_file:
        img_data = img_file.read()

    return dict(img_data=img_data, path=abs_path)


def safe_make_dirs(path: str, mode: int = 0o777) -> str:
    """Create a leaf directory and all intermediate ones in a safe way.

    Handles existing leaf directories while avoiding os.path.exists() race
    conditions.
    """
    try:
        os.makedirs(path, mode)
    except OSError as error:
        if error.errno != 17:  # File exists
            raise

    return path


def get_default_cache() -> str:
    """Get the default cache location from the project root."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_dir = os.path.join(project_root, ".cache", "Pokedex")
    return cache_dir


def get_sprite_path(
    sprite_type: str, sprite_id: Union[int, str], **kwargs: Any
) -> str:
    """Build the absolute filesystem path for a cached sprite."""
    rel_filepath = sprite_filepath_build(sprite_type, sprite_id, **kwargs)
    abs_path = os.path.join(SPRITE_CACHE, rel_filepath)
    return abs_path


def set_cache(new_path: Optional[str] = None) -> str:
    """Set up the sprite cache directory tree.

    Args:
        new_path: Desired cache root. Uses the default if None.

    Returns:
        Absolute path to the cache root directory.
    """
    global CACHE_DIR, API_CACHE, SPRITE_CACHE

    if new_path is None:
        new_path = get_default_cache()

    try:
        CACHE_DIR = safe_make_dirs(os.path.abspath(new_path))
        API_CACHE = safe_make_dirs(os.path.join(CACHE_DIR, "api"))
        SPRITE_CACHE = safe_make_dirs(os.path.join(CACHE_DIR, "sprite"))
    except Exception as e:
        logging.error(f"Error setting cache: {str(e)}")
        raise

    return CACHE_DIR


def initialize_cache() -> str:
    """Initialize the cache directory tree using defaults."""
    global CACHE_DIR, API_CACHE, SPRITE_CACHE
    CACHE_DIR = set_cache()
    return CACHE_DIR

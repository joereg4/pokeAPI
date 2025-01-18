# cache.py
# -*- coding: utf-8 -*-

import os
import logging
import time
import json
import redis
from redis import ConnectionPool
import socket

from .common import cache_uri_build, sprite_filepath_build

# Cache locations will be set at the end of this file.
CACHE_DIR = None
API_CACHE = None
SPRITE_CACHE = None
CACHE_EXPIRATION_DAYS = 7

# Configure Redis connection pool
REDIS_POOL = ConnectionPool.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    max_connections=10,
    socket_timeout=2,
    socket_connect_timeout=2,
    retry_on_timeout=True,
    health_check_interval=30,
)

# Create Redis client with connection pool
redis_client = redis.Redis(
    connection_pool=REDIS_POOL,
    socket_keepalive=True,
    retry_on_timeout=True,
    decode_responses=True,  # Automatically decode responses to strings
)


def save(data, endpoint, resource_id=None, subresource=None):
    if data == dict():  # No point in saving empty data.
        return None

    if not isinstance(data, (dict, list)):
        raise ValueError("Could not save non-dict data")

    uri = cache_uri_build(endpoint, resource_id, subresource)

    try:
        # Compress and set the data in Redis
        compressed_data = json.dumps(data).encode("utf-8")
        redis_client.set(
            uri,
            compressed_data,
            ex=(
                CACHE_EXPIRATION_DAYS * 24 * 60 * 60
            ),  # Use ex parameter for expiration
        )
    except redis.RedisError as error:
        logging.warning(f"Redis error, skipping save: {error}")

    return None


def save_sprite(data, sprite_type, sprite_id, **kwargs):
    abs_path = data["path"]

    # Make intermediate directories; this line removes the file+extension.
    dirs = abs_path.rpartition(os.path.sep)[0]
    safe_make_dirs(dirs)

    with open(abs_path, "wb") as img_file:
        img_file.write(data["img_data"])

    print(f"Sprite saved successfully: {os.path.exists(abs_path)}")
    return None


def load(endpoint, resource_id=None, subresource=None):
    uri = cache_uri_build(endpoint, resource_id, subresource)

    try:
        data = redis_client.get(uri)
        if data is None:
            raise KeyError("Data not found in cache")
        return json.loads(data)
    except redis.RedisError as error:
        logging.warning(f"Redis error, skipping load: {error}")
        raise KeyError("Cache could not be accessed.")


def load_sprite(sprite_type, sprite_id, **kwargs):
    abs_path = get_sprite_path(sprite_type, sprite_id, **kwargs)

    with open(abs_path, "rb") as img_file:
        img_data = img_file.read()

    return dict(img_data=img_data, path=abs_path)


def safe_make_dirs(path, mode=0o777):
    """Create a leaf directory and all intermediate ones in a safe way.

    A wrapper to os.makedirs() that handles existing leaf directories while
    avoiding os.path.exists() race conditions.

    :param path: relative or absolute directory tree to create
    :param mode: directory permissions in octal
    :return: The newly-created path
    """
    try:
        os.makedirs(path, mode)
    except OSError as error:
        if error.errno != 17:  # File exists
            raise

    return path


def get_default_cache():
    """Get the default cache location.

    Returns a path for the cache directory, adapting to dev or prod environments.

    :return: the default cache directory absolute path
    """
    # Check if we're in a production-like environment
    if os.path.exists("/var/www/pokeAPI"):
        project_root = "/var/www/pokeAPI"
    else:
        # Assume we're in development
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Define the cache directory
    cache_dir = os.path.join(project_root, ".cache", "Pokedex")

    return cache_dir


def get_sprite_path(sprite_type, sprite_id, **kwargs):
    rel_filepath = sprite_filepath_build(sprite_type, sprite_id, **kwargs)
    abs_path = os.path.join(SPRITE_CACHE, rel_filepath)
    return abs_path


def set_cache(new_path=None):
    """Simple function to change the cache location.

    This function now only sets up the sprite cache directory.
    Redis connection is established globally.

    :param new_path: relative or absolute path to the desired new cache
    directory for sprites
    :return: str
    """

    if new_path is None:
        new_path = get_default_cache()

    try:
        CACHE_DIR = safe_make_dirs(os.path.abspath(new_path))
        SPRITE_CACHE = safe_make_dirs(os.path.join(CACHE_DIR, "sprite"))

    except Exception as e:
        logging.error(f"Error setting cache: {str(e)}")

    return CACHE_DIR


def initialize_cache():
    CACHE_DIR = set_cache()

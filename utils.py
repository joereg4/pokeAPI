from flask import current_app
import redis
from cache import cache
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def get_cache_stats():
    """Monitor Redis cache usage"""
    try:
        redis_client = cache.cache._write_client
        info = redis_client.info()

        stats = {
            "status": "connected",
            "used_memory_human": info["used_memory_human"],
            "hit_rate": info.get("keyspace_hits", 0)
            / (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1)),
            "total_connections_received": info["total_connections_received"],
            "connected_clients": info["connected_clients"],
            "uptime_in_seconds": info["uptime_in_seconds"],
        }

        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {
            "status": "disconnected",
            "hit_rate": 0,
            "used_memory_human": "N/A",
            "connected_clients": 0,
            "total_connections_received": 0,
            "uptime_in_seconds": 0,
        }


def clear_expired_keys():
    """Clean up expired keys periodically"""
    try:
        redis_client = cache.cache._write_client
        cursor = 0
        deleted_count = 0

        while True:
            cursor, keys = redis_client.scan(cursor, match="pokedex:*")
            for key in keys:
                if redis_client.ttl(key) <= 0:
                    redis_client.delete(key)
                    deleted_count += 1
            if cursor == 0:
                break

        logger.info(f"Cleared {deleted_count} expired keys")
        return deleted_count
    except Exception as e:
        logger.error(f"Error clearing expired keys: {e}")
        return None


def invalidate_related_caches(resource_type, resource_id):
    """Invalidate related caches when a resource is updated"""
    deleted_keys = []

    # Direct cache key invalidation based on discovered patterns
    specific_keys = []

    if resource_type == "ability":
        # For abilities, use the exact pattern we discovered
        specific_keys.append(f"pokedex:view//ability/{resource_id}")
    elif resource_type == "pokemon":
        specific_keys.append(f"pokedex:view//pokemon/{resource_id}")
        specific_keys.append(f"pokedex:pokemon_{resource_id}")
        specific_keys.append(f"pokedex:pokemon_species_{resource_id}")
    elif resource_type == "move":
        specific_keys.append(f"pokedex:view//move/{resource_id}")
        specific_keys.append(f"pokedex:move_{resource_id}")
    elif resource_type == "item":
        specific_keys.append(f"pokedex:view//item/{resource_id}")
        specific_keys.append(f"pokedex:item_{resource_id}")
    elif resource_type == "type":
        specific_keys.append(f"pokedex:view//type/{resource_id}")
        specific_keys.append(f"pokedex:type_{resource_id}")

    # Delete specific keys that we know the exact patterns for
    deleted_count = 0
    redis_client = cache.cache._write_client

    for key in specific_keys:
        try:
            if redis_client.exists(key):
                redis_client.delete(key)
                deleted_keys.append(key)
                deleted_count += 1
                logger.info(f"Deleted specific cache key: {key}")
        except Exception as e:
            logger.error(f"Error deleting specific key {key}: {e}")

    # These are additional patterns we need to clear
    # that might not contain the resource_id directly
    additional_patterns = {
        "pokemon": ["evolution_chain_*", "summary_*"],
        "move": ["pokemon_*", "summary_*"],
        "ability": ["pokemon_*", "summary_*"],
        "item": ["summary_*"],
        "type": ["pokemon_*", "type_*", "summary_*"],
    }

    # Also clear related resources that don't directly contain the resource name/id
    if resource_type in additional_patterns:
        for pattern in additional_patterns[resource_type]:
            try:
                keys = redis_client.keys(f"pokedex:{pattern}")
                if keys:
                    cache.delete_many(*keys)
                    deleted_keys.extend(keys)
            except Exception as e:
                logger.error(f"Error invalidating cache pattern {pattern}: {e}")

    total_cleared = len(deleted_keys)
    logger.info(f"Cleared {total_cleared} cache keys for {resource_type}/{resource_id}")

    return total_cleared


from pokedex.api import get_data


def warm_common_endpoints():
    """Pre-warm cache for commonly accessed endpoints"""
    common_pokemon_ids = range(1, 152)  # First generation Pokemon
    warmed_count = 0

    for pokemon_id in common_pokemon_ids:
        try:
            # Cache Pokemon data
            key = f"pokemon_{pokemon_id}"
            if not cache.get(key):
                data = get_data("pokemon", pokemon_id)
                cache.set(key, data)
                warmed_count += 1

            # Cache species data
            species_key = f"pokemon_species_{pokemon_id}"
            if not cache.get(species_key):
                species_data = get_data("pokemon-species", pokemon_id)
                cache.set(species_key, species_data)
                warmed_count += 1

        except Exception as e:
            logger.error(f"Error warming cache for Pokemon {pokemon_id}: {e}")

    logger.info(f"Warmed up {warmed_count} cache entries")
    return warmed_count


def inspect_cache_keys(resource_type=None, resource_name=None):
    """
    Inspect Redis cache keys to find patterns related to a specific resource.
    This is useful for debugging cache invalidation issues.

    Args:
        resource_type: The resource type (pokemon, ability, move, etc.) to filter by
        resource_name: The resource name to filter by

    Returns:
        A list of matching cache keys
    """
    try:
        redis_client = cache.cache._write_client
        cursor = 0
        all_keys = []

        # Collect all keys
        while True:
            cursor, keys = redis_client.scan(cursor, match="pokedex:*")
            all_keys.extend(
                [k.decode("utf-8") if isinstance(k, bytes) else k for k in keys]
            )
            if cursor == 0:
                break

        # Filter keys if resource_type or resource_name is provided
        filtered_keys = all_keys

        if resource_type:
            filtered_keys = [
                k for k in filtered_keys if resource_type.lower() in k.lower()
            ]

        if resource_name:
            filtered_keys = [
                k for k in filtered_keys if resource_name.lower() in k.lower()
            ]

        return filtered_keys
    except Exception as e:
        logger.error(f"Error inspecting cache keys: {e}")
        return []


def clear_cache_for_resource(resource_type, resource_name):
    """
    Clear all cache entries related to a specific resource.
    This uses the inspect_cache_keys function to find all related keys and delete them.

    Args:
        resource_type: The resource type (pokemon, ability, move, etc.)
        resource_name: The specific resource name or ID

    Returns:
        The number of keys deleted
    """
    try:
        # Find all keys related to this resource
        keys = inspect_cache_keys(resource_type, resource_name)

        if keys:
            # Delete all matching keys
            redis_client = cache.cache._write_client
            deleted_count = 0

            for key in keys:
                redis_client.delete(key)
                deleted_count += 1

            logger.info(
                f"Cleared {deleted_count} cache keys for {resource_type}/{resource_name}"
            )
            return deleted_count

        return 0
    except Exception as e:
        logger.error(f"Error clearing cache for {resource_type}/{resource_name}: {e}")
        return 0

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
        return None


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
    patterns = {
        "pokemon": [
            f"pokemon_{resource_id}",
            f"pokemon_species_{resource_id}",
            f"evolution_chain_*",
        ],
        "move": [
            f"move_{resource_id}",
            f"pokemon_*",
        ],
    }

    deleted_keys = []
    if resource_type in patterns:
        for pattern in patterns[resource_type]:
            try:
                keys = cache.cache._write_client.keys(f"pokedex:{pattern}")
                if keys:
                    cache.delete_many(*keys)
                    deleted_keys.extend(keys)
            except Exception as e:
                logger.error(f"Error invalidating cache pattern {pattern}: {e}")

    return deleted_keys


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

"""Shared Redis client module for caching and rate limiting"""

import os
import redis
from redis import ConnectionPool

# Configure Redis connection pool
REDIS_POOL = ConnectionPool.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    max_connections=10,
    socket_timeout=2,
    socket_connect_timeout=30,  # Increased to match limiter's timeout
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


def scan_keys(client, pattern, count=100):
    """Collect all keys matching ``pattern`` using cursor-based SCAN.

    Always prefer this over ``client.keys(pattern)``: KEYS walks the entire
    keyspace in a single blocking call, stalling every other Redis operation,
    while SCAN iterates in small non-blocking batches.
    """
    keys = []
    cursor = 0
    while True:
        cursor, batch = client.scan(cursor, match=pattern, count=count)
        keys.extend(batch)
        if cursor == 0:
            break
    return keys

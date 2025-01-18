from flask_caching import Cache
from pokedex.utils import Config

cache = Cache(
    config={
        "CACHE_TYPE": "redis",
        "CACHE_REDIS_URL": Config.REDIS_URL,
        "CACHE_DEFAULT_TIMEOUT": Config.CACHE_TIMEOUT,
        "CACHE_KEY_PREFIX": "pokeapi_",
        "CACHE_OPTIONS": {
            "socket_timeout": 2,
            "socket_connect_timeout": 2,
            "retry_on_timeout": True,
            "socket_keepalive": True,
            "health_check_interval": 30,
            "max_connections": 10,
        },
        "CACHE_REDIS_COMPRESSION_ENABLED": True,
        "CACHE_REDIS_COMPRESSION_TYPE": "gzip",
    }
)

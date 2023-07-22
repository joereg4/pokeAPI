from flask_caching import Cache

cache = Cache()


def configure_caching(app):
    # Example configuration for simple in-memory caching:
    cache_config = {
        "CACHE_TYPE": "simple",
        "CACHE_DEFAULT_TIMEOUT": 300  # Cache timeout in seconds
    }

    # For Redis or Memcached, adjust the configuration accordingly.

    app.config.from_mapping(cache_config)
    cache.init_app(app)

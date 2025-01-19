import logging
import os
from flask import Flask, render_template
from flask_compress import Compress
import pokedex
from cache import cache
from routes import blueprints
from pokedex.utils import load_resources
from limiter import limiter

# Load environment variables
pokedex.env.load_environment()


def create_app(test_config=None):
    app = Flask(__name__)

    # Initialize rate limiter
    limiter.init_app(app)

    # Configure compression
    app.config["COMPRESS_MIMETYPES"] = [
        "text/html",
        "text/css",
        "text/xml",
        "application/json",
        "application/javascript",
    ]
    app.config["COMPRESS_LEVEL"] = 6
    app.config["COMPRESS_MIN_SIZE"] = 500
    Compress(app)

    # Get the current environment with fallback
    env = pokedex.env.get_env_variable("FLASK_ENV", "production")
    if env:
        env = env.lower()

    if env not in ["development", "production"]:
        env = "production"  # Default to production if invalid

    # Set up logging based on environment
    if env == "development":
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        app.logger.setLevel(logging.DEBUG)
        cache_timeout = int(os.getenv("CACHE_TIMEOUT", 300))
        app.logger.debug(f"CACHE_TIMEOUT is set to: {cache_timeout}")
    else:
        logging.basicConfig(level=logging.WARNING)
        app.logger.setLevel(logging.WARNING)

    # Configure Redis cache with enhanced settings
    cache_config = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "CACHE_DEFAULT_TIMEOUT": int(os.getenv("CACHE_DEFAULT_TIMEOUT", 3600)),
        "CACHE_KEY_PREFIX": "pokedex:",
        "CACHE_OPTIONS": {
            "socket_timeout": 2,
            "socket_connect_timeout": 2,
            "retry_on_timeout": True,
            "max_connections": 10,
        },
        "CACHE_REDIS_COMPRESSION_ENABLED": True,
    }

    cache.init_app(app, config=cache_config)

    # Set the cache location for the low-level cache
    pokedex.cache.initialize_cache()

    # Override config if test_config is provided
    if test_config:
        app.config.update(test_config)

    with app.app_context():
        load_resources()

    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        message = e.description if hasattr(e, "description") else "Page not found"
        return render_template("404.html", message=message), 404

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template("429.html", message=str(e.description)), 429

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()

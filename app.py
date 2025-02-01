import logging
import os
from flask import Flask, render_template, request
from flask_compress import Compress
import pokedex
from cache import cache, get_cache_config
from routes import blueprints
from pokedex.utils import load_resources, Config
from limiter import limiter
from routes.health import increment_api_counter

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
    else:
        logging.basicConfig(level=logging.WARNING)
        app.logger.setLevel(logging.WARNING)

    # Configure Redis cache with enhanced settings
    cache.init_app(app, config=get_cache_config())

    # Set the cache location for the low-level cache
    pokedex.cache.initialize_cache()

    # Override config if test_config is provided
    if test_config:
        app.config.update(test_config)

    with app.app_context():
        load_resources()

    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    @app.before_request
    def track_request():
        """Track API calls before each request"""
        # Skip tracking for static files and health checks
        if not request.path.startswith("/static") and not request.path.startswith(
            "/health"
        ):
            try:
                increment_api_counter()
                app.logger.info(f"API call tracked for: {request.path}")
            except Exception as e:
                app.logger.error(f"Error tracking API call: {e}")

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        message = e.description if hasattr(e, "description") else "Page not found"
        return render_template("404.html", message=message), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Internal Server Error: {str(e)}")
        return (
            render_template("500.html", message="An internal server error occurred"),
            500,
        )

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template("429.html", message=str(e.description)), 429

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()

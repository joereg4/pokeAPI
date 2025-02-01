import logging
import os
import json
from flask import Flask, render_template, request, abort
from flask_compress import Compress
from flask_migrate import Migrate
import pokedex
from cache import cache, get_cache_config
from routes import blueprints
from pokedex.utils import load_resources, Config, resources_dict
from limiter import limiter
from routes.health import increment_api_counter
from model import db
from routes.auth import init_auth

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

    if env not in ["development", "production", "testing"]:
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

    # Apply test configuration first if provided
    if test_config:
        app.config.update(test_config)
    else:
        # Configure SQLAlchemy for non-test environments
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
            "DATABASE_URL", "postgresql://localhost/pokeapi"
        )
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")

    # Initialize SQLAlchemy and Migrate
    db.init_app(app)
    migrate = Migrate(app, db)

    # Initialize authentication
    init_auth(app)

    with app.app_context():
        load_resources()
        # Create database tables
        db.create_all()

    # Register blueprints (includes auth_bp and admin_bp from routes)
    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    @app.context_processor
    def inject_resources():
        """Make resources available to all templates."""
        return dict(resources_json=json.dumps(resources_dict))

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

    # Test routes for error handlers
    if test_config and test_config.get("TESTING", False):
        @app.route("/test-403")
        def test_403():
            abort(403)

        @app.route("/test-404")
        def test_404():
            abort(404)

        @app.route("/test-500")
        def test_500():
            abort(500)

        @app.route("/test-429")
        def test_429():
            abort(429)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()

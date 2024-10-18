import logging
import os
from flask import Flask, render_template
import pokedex
from cache import cache
from routes import blueprints
from pokedex.utils import load_resources

# Load environment variables
pokedex.env.load_environment()


def create_app(test_config=None):
    app = Flask(__name__)

    # Get the current environment with fallback
    env = pokedex.env.get_env_variable("FLASK_ENV").lower()

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

    # Configure the cache to use Redis
    cache.init_app(app, config={
        'CACHE_TYPE': 'RedisCache',
        'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    })

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
        message = e.description if hasattr(e, 'description') else "Page not found"
        return render_template("404.html", message=message), 404

    return app


if __name__ == '__main__':
    app = create_app()
    app.run()

from flask import Flask, render_template
from cache import cache
from routes import pokemon_bp
import pokedex
import logging

logging.basicConfig(level=logging.WARNING)

# Load environment variables
pokedex.env.load_environment()


def create_app(test_config=None):
    app = Flask(__name__)

    # Configure the cache
    cache.init_app(app, config={'CACHE_TYPE': 'simple'})

    # If there's a test config, override the default configurations
    if test_config:
        app.config.update(test_config)
    else:
        # Use the default configurations
        if pokedex.env.get_env_variable("FLASK_ENV") == "development":
            app.config["DEBUG_PRINT_ROUTES"] = True
        else:
            app.config["DEBUG_PRINT_ROUTES"] = False

    app.register_blueprint(pokemon_bp)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    if app.config["DEBUG_PRINT_ROUTES"]:
        for key, value in app.config.items():
            print(f"{key}: {value}")
            print("---- FLASK CONFIG END ----")

        for rule in app.url_map.iter_rules():
            print(rule)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run()

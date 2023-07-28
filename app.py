from flask import Flask
from routes import pokemon_bp
from pokedex import utils
import logging

logging.basicConfig(level=logging.INFO)

# Load environment variables
utils.env.load_environment()


def create_app():
    app = Flask(__name__)

    with app.app_context():
        utils.get_db()

    app.teardown_appcontext(utils.close_db)
    app.register_blueprint(pokemon_bp)

    # Set the configuration
    if utils.env.get_env_variable("FLASK_ENV") == "development":
        app.config["DEBUG_PRINT_ROUTES"] = True
        for key, value in app.config.items():
            print(f"{key}: {value}")
            print("---- FLASK CONFIG END ----")
    else:
        app.config["DEBUG_PRINT_ROUTES"] = False

    if app.config["DEBUG_PRINT_ROUTES"]:
        for rule in app.url_map.iter_rules():
            print(rule)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run()

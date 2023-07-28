from flask import Flask
from routes import pokemon_bp
from pokedex import utils
import logging

logging.basicConfig(level=logging.INFO)

# Load environment variables
utils.env.load_environment()


def create_app(test_config=None):
    app = Flask(__name__)

    # If there's a test config, override the default configurations
    if test_config:
        app.config.update(test_config)
    else:
        # Use the default configurations
        if utils.env.get_env_variable("FLASK_ENV") == "development":
            app.config["DEBUG_PRINT_ROUTES"] = True
        else:
            app.config["DEBUG_PRINT_ROUTES"] = False

    with app.app_context():
        utils.get_db()

    app.teardown_appcontext(utils.close_db)
    app.register_blueprint(pokemon_bp)

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

if __name__ == '__main__':
    app = create_app()
    app.run()

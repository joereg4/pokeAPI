from flask import Flask
from routes import pokemon_bp
from pokedex.utils import env, logging
from pokedex.utils.db_utils import get_db, close_db


# Load environment variables
env.load_environment()
print("Direct FLASK_ENV:", env.get_env_variable("FLASK_ENV"))

# Configure logging
logging.configure_logging()

def create_app():
    app = Flask(__name__)

    with app.app_context():
        get_db()

    app.teardown_appcontext(close_db)
    app.register_blueprint(pokemon_bp)

    # Set the configuration
    if env.get_env_variable("FLASK_ENV") == "development":
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

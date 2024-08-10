from flask import Flask, current_app
from cache import cache
from routes import pokemon_bp
import pokedex
import logging
import csv
import os

logging.basicConfig(level=logging.INFO)

# Load environment variables
pokedex.env.load_environment()

# Define the global variable at the module level
resources_dict = {}


# Function to get the full path to the resources.csv file
def get_csv_file_path():
    # Get the root path of the Flask app
    root_path = current_app.root_path
    # Construct the full path to the CSV file in the static directory
    csv_file_path = os.path.join(root_path, 'static', 'resources.csv')
    return csv_file_path


# Function to load resources from the CSV file
def load_resources():
    global resources_dict  # Reference the global variable
    csv_file_path = get_csv_file_path()  # Use the helper function to get the path

    try:
        with open(csv_file_path, mode='r') as file:
            reader = csv.reader(file)
            resources_dict = {row[1]: row[0] for row in reader}  # {name: resource_type}
    except FileNotFoundError:
        print(f"File not found: {csv_file_path}")
        resources_dict = {}  # Fallback to an empty dictionary if the file is not found


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

    # Load resources after the app context is available
    with app.app_context():
        load_resources()

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

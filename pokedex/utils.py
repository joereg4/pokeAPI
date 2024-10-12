import os
import logging
import csv
import glob
from flask import current_app
from pokedex.env import load_environment, get_env_variable

resources_dict = []

# Load environment variables using env.py
load_environment()


class Config:
    BASE_URL = get_env_variable('BASE_URL', 'https://pokeapi.co/api/v2')
    SPRITE_URL = get_env_variable('SPRITE_URL', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites')
    POKEMON_PER_PAGE = int(get_env_variable('POKEMON_PER_PAGE', 60))
    ITEMS_PER_PAGE = int(get_env_variable('ITEMS_PER_PAGE', 50))
    WEBHOOK_SECRET = get_env_variable('WEBHOOK_SECRET')
    CACHE_TIMEOUT = int(get_env_variable('CACHE_TIMEOUT', 300))


def get_csv_file_paths():
    root_path = current_app.root_path
    # Find all CSV files in the static/resources directory
    csv_file_paths = glob.glob(os.path.join(root_path, 'static', 'resources', '*.csv'))
    return csv_file_paths


def load_resources():
    global resources_dict

    # Get all CSV file paths
    csv_file_paths = get_csv_file_paths()

    # Clear the existing dictionary to avoid residual data
    resources_dict.clear()

    for csv_file_path in csv_file_paths:
        try:
            with open(csv_file_path, mode='r') as file:
                reader = csv.reader(file)
                next(reader)  # Skip the header row

                # Populate the global resources_dict directly
                for row in reader:
                    resources_dict.append({"name": row[1], "type": row[0]})

        except FileNotFoundError:
            logging.error(f"File not found: {csv_file_path}")
        except Exception as e:
            logging.error(f"An error occurred while processing {csv_file_path}: {e}")

    if not resources_dict:
        resources_dict = []

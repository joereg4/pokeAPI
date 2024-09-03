import logging

import markdown
from flask import Blueprint, render_template, request, json, current_app, url_for, abort
from markupsafe import Markup
from pokemontcgsdk import Card

from cache import cache
import requests
from requests.exceptions import HTTPError
import pokedex
import sys
import pandas as pd
import hmac
import hashlib
import subprocess
import os
import re

pokemon_bp = Blueprint(
    "pokemon", __name__, template_folder="templates", static_folder="static"
)

BASE_URL = "https://pokeapi.co/api/v2"
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites"
POKEMON_PER_PAGE = 60

# Define the valid sprite names to filter
valid_sprites = [
    "front_default",
    "back_default",
    "front_female",
    "back_female",
    "front_shiny",
    "back_shiny",
    "front_shiny_female",
    "back_shiny_female",
]

# Define colors for Types
type_colors = {
    "normal": "#A8A77A",
    "fire": "#EE8130",
    "water": "#6390F0",
    "electric": "#F7D02C",
    "grass": "#7AC74C",
    "ice": "#96D9D6",
    "fighting": "#C22E28",
    "poison": "#A33EA1",
    "ground": "#E2BF65",
    "flying": "#A98FF3",
    "psychic": "#F95587",
    "bug": "#A6B91A",
    "rock": "#B6A136",
    "ghost": "#735797",
    "dragon": "#6F35FC",
    "dark": "#705746",
    "steel": "#B7B7CE",
    "fairy": "#D685AD"
}


def get_path(filename):
    csv_url = url_for('static', filename=f'resources/{filename}')

    csv_path = os.path.join(current_app.root_path, csv_url.lstrip('/'))

    return csv_path


def get_egg_summary(name, df):
    row = df[(df['name'].str.lower() == name.lower())]

    if not row.empty:
        return row.iloc[0]['summary']
    else:
        return None


def get_summary(name, df):
    row = df[(df['name'].str.lower() == name.lower())]

    if not row.empty:
        return row.iloc[0]['summary']
    else:
        return None


def get_pokemon_cards(pokemon_name):
    try:
        # Attempt to fetch the cards using the API
        data = Card.where(q='name:{}'.format(pokemon_name))

        card_list = []

        for card in data:
            card_list.append({
                'id': card.id,
                'name': card.name,
                'artist': card.artist,
                'large_image': card.images.large,
                'set_name': card.set.name
            })

        return card_list

    except Exception as e:
        # Log the exception for debugging purposes
        logging.info(f"Error fetching Pokémon cards for {pokemon_name}: {e}")
        # Return an empty list to indicate no cards were found due to the error
        return []


def create_pokemon_list(data):
    try:
        # If data is a list, assume it contains the Pokémon entries directly
        if isinstance(data, list):
            pokemon_entries = data
        else:
            # Possible keys that might contain the Pokémon species list
            possible_keys = ["pokemon", "pokemon_species", "pokemon_entries", "pokemon_encounters", "held_by_pokemon",
                             "learned_by_pokemon", "varieties"]

            # Identify the correct key by checking which one exists in the data
            key = next((k for k in possible_keys if k in data), None)

            if not key:
                raise ValueError("No valid key found in data for Pokémon list.")

            # Assign the Pokémon entries based on the identified key
            if key == "pokemon_entries":
                pokemon_entries = [entry["pokemon_species"] for entry in data[key]]
            else:
                pokemon_entries = data[key]

        # Build the Pokémon list based on the identified key
        pokemon_list = []
        for pokemon_entry in pokemon_entries:
            # The key structure is different depending on the data source
            if isinstance(pokemon_entry, dict):
                pokemon_name = pokemon_entry["name"] if "name" in pokemon_entry else pokemon_entry.get("pokemon",
                                                                                                       {}).get("name")
            else:
                logging.info(f"Warning: Invalid Pokémon entry structure under key '{key}': {pokemon_entry}")
                continue

            if not pokemon_name:
                logging.info(f"Warning: Could not find Pokémon name in entry under key '{key}': {pokemon_entry}")
                continue

            # Fetch the Pokémon data
            pokemon = pokedex.APIResource.fetch_data("pokemon", pokemon_name)

            # Add encounter details if available
            if key == "pokemon_encounters":
                version_details = pokemon_entry.get("version_details", [])
                pokemon['version_details'] = []

                for version_detail in version_details:
                    encounter_info = {
                        'version_name': version_detail['version']['name'],
                        'method': version_detail['encounter_details'][0]['method']['name'],
                        'max_level': version_detail['encounter_details'][0]['max_level'],
                        'min_level': version_detail['encounter_details'][0]['min_level'],
                        'chance': version_detail['encounter_details'][0]['chance']
                    }
                    pokemon['version_details'].append(encounter_info)

            # Check if the 'sprites' key exists in the Pokémon data
            if "sprites" in pokemon:
                pokemon_list.append(pokemon)
            else:
                logging.info(f"No sprites found for Pokémon '{pokemon_name}' under key '{key}'")

        pokemon_list.sort(key=lambda x: x.get("id", float("inf")))

        return pokemon_list
    except ValueError as e:
        logging.info(f"Error fetching Pokémon data under key '{key}': {e}")
        return []


def fetch_all_results(url):
    results = []
    while url:
        response = requests.get(url)
        data = response.json()
        results.extend(data["results"])
        url = data.get("next")  # Get the next page URL, if it exists
    return results


@pokemon_bp.errorhandler(ValueError)
def handle_value_error(error):
    # Log the error if needed
    logging.error(str(error))
    # Return a custom error message and a 400 Bad Request status code
    return str(error), 400


@pokemon_bp.context_processor
def inject_resources():
    with current_app.app_context():
        pokedex.load_resources()

    return dict(resources_json=json.dumps(pokedex.resources_dict))


@pokemon_bp.route("/")
def index():
    pokedex.load_resources()  # Load resources from the CSV
    # Fetch total Pokémon count
    pokemon_count_response = requests.get("https://pokeapi.co/api/v2/pokemon?limit=1")
    pokemon_count = pokemon_count_response.json()["count"]

    # Fetch total types count
    types_count_response = requests.get("https://pokeapi.co/api/v2/type?limit=1")
    types_count = types_count_response.json()["count"]

    # Fetch total abilities count
    abilities_count_response = requests.get("https://pokeapi.co/api/v2/ability?limit=1")
    abilities_count = abilities_count_response.json()["count"]

    # Fetch total colors count
    color_count_response = requests.get("https://pokeapi.co/api/v2/pokemon-color?limit=1")
    color_count = color_count_response.json()["count"]

    # Fetch total habitat count
    habitat_count_response = requests.get("https://pokeapi.co/api/v2/pokemon-habitat?limit=1")
    habitat_count = habitat_count_response.json()["count"]

    # Fetch total habitat count
    shape_count_response = requests.get("https://pokeapi.co/api/v2/pokemon-shape?limit=1")
    shape_count = shape_count_response.json()["count"]

    return render_template(
        "index.html",
        pokemon_count=pokemon_count,
        types_count=types_count,
        abilities_count=abilities_count,
        color_count=color_count,
        habitat_count=habitat_count,
        shape_count=shape_count,
    )


@pokemon_bp.route("/ability/", defaults={"id_or_name": None})
@pokemon_bp.route("/ability/<id_or_name>")
@cache.cached(timeout=300)
def get_ability(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the abilities list
        url = "https://pokeapi.co/api/v2/ability"
        abilities = fetch_all_results(url)
        return render_template("abilities.html", abilities=abilities)
    else:
        # id_or_name is provided, render the ability detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("ability", id_or_name)

            if "name" not in data:
                abort(404, description=f"Ability '{id_or_name}' not found")

            # Use the create_pokemon_list function to get Pokémon with this ability
            pokemon_list = create_pokemon_list(data)

            # Fetch Summary
            csv_file_path = get_path('ability.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template("ability_detail.html", data=data, pokemon_list=pokemon_list,
                                   summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/berry/", defaults={"id_or_name": None})
@pokemon_bp.route("/berry/<id_or_name>")
# @cache.cached(timeout=300)
def get_berry(id_or_name):
    if id_or_name is None:
        # Fetch and display a list of all berries
        url = "https://pokeapi.co/api/v2/berry"
        data = fetch_all_results(url)

        return render_template("berries.html", data=data)
    else:
        # Fetch and display details for a specific berry
        try:
            data = pokedex.APIResource.fetch_data("berry", id_or_name)

            if "name" not in data:
                abort(404, description=f"Berry '{id_or_name}' not found")

            # Fetch Summary
            csv_file_path = get_path('berry.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template("berry_detail.html", data=data, summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/berry_firmness/", defaults={"id_or_name": None})
@pokemon_bp.route("/berry_firmness/<id_or_name>")
# @cache.cached(timeout=300)
def get_berry_firmness(id_or_name):
    if id_or_name is None:
        # Fetch and display a list of all berry firmness categories
        url = "https://pokeapi.co/api/v2/berry-firmness"
        data = fetch_all_results(url)

        return render_template("berry_firmness.html", data=data)
    else:
        # Fetch and display details for a specific berry firmness
        try:
            data = pokedex.APIResource.fetch_data("berry-firmness", id_or_name)

            if "name" not in data:
                abort(404, description=f"Berry Firmness '{id_or_name}' not found")

            return render_template("berry_firmness_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/berry_flavor/", defaults={"id_or_name": None})
@pokemon_bp.route("/berry_flavor/<id_or_name>")
@cache.cached(timeout=300)
def get_berry_flavor(id_or_name):
    if id_or_name is None:
        # Fetch and display a list of all berry flavors
        url = "https://pokeapi.co/api/v2/berry-flavor"
        data = fetch_all_results(url)

        return render_template("berry_flavors.html", data=data)
    else:
        # Fetch and display details for a specific berry flavor
        try:
            data = pokedex.APIResource.fetch_data("berry-flavor", id_or_name)

            if "name" not in data:
                abort(404, description=f"Berry Flavor '{id_or_name}' not found")

            return render_template("berry_flavor_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/characteristic/", defaults={"id_": None})
@pokemon_bp.route("/characteristic/<int:id_>")
@cache.cached(timeout=300)
def get_characteristic(id_):
    if id_ is None:
        # Fetch and display a list of all characteristics
        url = "https://pokeapi.co/api/v2/characteristic"
        data = fetch_all_results(url)

        # Extract the ID from the URL for each characteristic
        for characteristic in data:
            characteristic['id'] = int(characteristic['url'].split('/')[-2])

        return render_template("characteristics.html", data=data)
    else:
        # Fetch and display details for a specific characteristic
        try:
            data = pokedex.APIResource.fetch_data("characteristic", id_)

            if "id" not in data:
                abort(404, description=f"Characteristic '{id_}' not found")

            return render_template("characteristic_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status
        except HTTPError as e:
            # If the HTTP error is 404, raise a 404 Not Found
            if e.response.status_code == 404:
                abort(404, description=f"Characteristic '{id_}' not found")
            else:
                # For other HTTP errors, you might want to log them or handle differently
                logging.warning(f"HTTP error occurred: {e}")
                return str(e), e.response.status_code


@pokemon_bp.route("/contest_effect/", defaults={"id_": None})
@pokemon_bp.route("/contest_effect/<int:id_>")
@cache.cached(timeout=300)
def get_contest_effect(id_):
    if id_ is None:
        # Fetch and display a list of all contest effects
        url = "https://pokeapi.co/api/v2/contest-effect"
        data = fetch_all_results(url)

        # Extract the ID from the URL for each contest effect
        for effect in data:
            effect['id'] = int(effect['url'].split('/')[-2])

        return render_template("contest_effects.html", data=data)
    else:
        # Fetch and display details for a specific contest effect
        try:
            data = pokedex.APIResource.fetch_data("contest-effect", id_)

            if "id" not in data:
                abort(404, description=f"Contest '{id_}' not found")

            return render_template("contest_effect_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/contest_type/<id_or_name>")
@cache.cached(timeout=300)
def get_contest_type(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("contest-type", id_or_name)

        if "name" not in data:
            abort(404, description=f"Contest Type '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/egg_group/", defaults={"id_or_name": None})
@pokemon_bp.route("/egg_group/<id_or_name>")
@cache.cached(timeout=300)
def get_egg_group(id_or_name):
    if id_or_name is None:
        # Fetch and render the list of all egg groups
        url = "https://pokeapi.co/api/v2/egg-group"
        data = fetch_all_results(url)
        return render_template("egg_groups.html", data=data)
    else:
        try:
            # Check if id_or_name can be converted to an integer
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("egg-group", id_or_name)

            if "name" not in data:
                abort(404, description=f"Egg Group '{id_or_name}' not found")

            # Use the create_pokemon_list function with the correct key
            pokemon_list = create_pokemon_list(data)

            # Fetch Summary
            csv_file_path = get_path('egg-group.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template(
                "egg_group_detail.html",
                data=data,
                pokemon_list=pokemon_list,
                summary_html=summary_html
            )
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/encounter_condition/<id_or_name>")
@cache.cached(timeout=300)
def get_encounter_condition(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("encounter-condition", id_or_name)

        if "name" not in data:
            abort(404, description=f"Encounter Condition '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/encounter_condition_value/<id_or_name>")
@cache.cached(timeout=300)
def get_encounter_condition_value(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("encounter-condition-value", id_or_name)

        if "name" not in data:
            abort(404, description=f"Encounter Condition Value '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/encounter_method/<id_or_name>")
@cache.cached(timeout=300)
def get_encounter_method(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("encounter-method", id_or_name)

        if "name" not in data:
            abort(404, description=f"Encounter Method '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/evolution_chain/<int:id_>")
@cache.cached(timeout=300)
def get_evolution_chain(id_):
    try:
        data = pokedex.APIResource.fetch_data("evolution-chain", id_)

        if "id" not in data:
            abort(404, description=f"Evolution Chain '{id_}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status
    except HTTPError as e:
        # If the HTTP error is 404, raise a 404 Not Found
        if e.response.status_code == 404:
            abort(404, description=f"Evolution Chain '{id_}' not found")
        else:
            # For other HTTP errors, you might want to log them or handle differently
            logging.warning(f"HTTP error occurred: {e}")
            return str(e), e.response.status_code


@pokemon_bp.route("/evolution_trigger/<id_or_name>")
@cache.cached(timeout=300)
def get_evolution_trigger(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("evolution-trigger", id_or_name)

        if "name" not in data:
            abort(404, description=f"Evolution Trigger '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/gender/<id_or_name>")
@cache.cached(timeout=300)
def get_gender(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("gender", id_or_name)

        if "name" not in data:
            abort(404, description=f"Gender '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/generation/", defaults={"id_or_name": None})
@pokemon_bp.route("/generation/<id_or_name>")
@cache.cached(timeout=300)
def get_generation(id_or_name):
    if id_or_name is None:
        # Fetch all generations
        url = "https://pokeapi.co/api/v2/generation"
        data = fetch_all_results(url)
        return render_template("generations.html", data=data)
    else:
        try:
            # Check if id_or_name can be converted to an integer
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("generation", id_or_name)

            if "name" not in data:
                abort(404, description=f"Generation '{id_or_name}' not found")

            # Use the create_pokemon_list function with the correct key
            pokemon_list = create_pokemon_list(data)

            return render_template("generation_detail.html", data=data, pokemon_list=pokemon_list)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/growth_rate/<id_or_name>")
@cache.cached(timeout=300)
def get_growth_rate(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("growth-rate", id_or_name)

        if "name" not in data:
            abort(404, description=f"Growth Rate '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item/", defaults={"id_or_name": None})
@pokemon_bp.route("/item/<id_or_name>")
@cache.cached(timeout=300)
def get_item(id_or_name):
    if id_or_name is None:
        # Fetch all items
        url = "https://pokeapi.co/api/v2/item"
        data = fetch_all_results(url)
        return render_template("items.html", data=data)
    else:
        try:
            # Check if id_or_name can be converted to an integer
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("item", id_or_name)

            if "name" not in data:
                abort(404, description=f"Item '{id_or_name}' not found")

            # Use the create_pokemon_list function with the correct key
            pokemon_list = create_pokemon_list(data)

            # Fetch Summary
            csv_file_path = get_path('item.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template("item_detail.html", data=data, pokemon_list=pokemon_list, summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item_attribute/<id_or_name>")
@cache.cached(timeout=300)
def get_item_attribute(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string

    try:
        data = pokedex.APIResource.fetch_data("item-attribute", id_or_name)

        if "name" not in data:
            abort(404, description=f"Item Attribute '{id_or_name}' not found")

        items_list = data.pop("items", [])  # Extract items to a separate variable
        return render_template("item_attribute_detail.html", data=data, items_list=items_list)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item_category/<id_or_name>")
@cache.cached(timeout=300)
def get_item_category(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("item-category", id_or_name)

        if "name" not in data:
            abort(404, description=f"Item Category '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item_fling_effect/<id_or_name>")
@cache.cached(timeout=300)
def get_item_fling_effect(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("item-fling-effect", id_or_name)

        if "name" not in data:
            abort(404, description=f"Item Fling '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item_pocket/<id_or_name>")
@cache.cached(timeout=300)
def get_item_pocket(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("item-pocket", id_or_name)

        if "name" not in data:
            abort(404, description=f"Item Pocket '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/language/<id_or_name>")
@cache.cached(timeout=300)
def get_language(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("language", id_or_name)

        if "name" not in data:
            abort(404, description=f"Language '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/location/", defaults={"id_or_name": None})
@pokemon_bp.route("/location/<id_or_name>")
@cache.cached(timeout=300)
def get_location(id_or_name):
    if id_or_name is None:
        # Fetch all locations
        url = "https://pokeapi.co/api/v2/location"
        data = fetch_all_results(url)
        return render_template("locations.html", data=data)
    else:
        try:
            # Check if id_or_name can be converted to an integer
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("location", id_or_name)

            if not data or "name" not in data:
                abort(404, description=f"Location '{id_or_name}' not found")

            return render_template("location_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status
        except HTTPError as e:
            if e.response.status_code == 404:
                abort(404, description=f"Location '{id_or_name}' not found")
            else:
                return str(e), 500  # Internal Server Error for other issues


@pokemon_bp.route("/location_area/<id_or_name>")
@cache.cached(timeout=300)
def get_location_area(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("location-area", id_or_name)

        if "name" not in data:
            abort(404, description=f"Location Area '{id_or_name}' not found")

        pokemon_list = create_pokemon_list(data)

        return render_template("location_area_detail.html", data=data, pokemon_list=pokemon_list)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/machine/<int:id_>")
def get_machine(id_):
    try:
        # Fetch machine data
        machine_data = pokedex.APIResource.fetch_data("machine", id_)

        # Fetch related data: item, move, and version group
        item_data = pokedex.APIResource.fetch_data("item", machine_data['item']['name'])
        move_data = pokedex.APIResource.fetch_data("move", machine_data['move']['name'])
        version_group_data = pokedex.APIResource.fetch_data("version-group", machine_data['version_group']['name'])

        # Handle cases where any of the data is missing or invalid
        if not all([item_data, move_data, version_group_data]):
            abort(404, description=f"Machine '{id_}' not found or incomplete data.")

        return render_template(
            "machine_detail.html",
            machine_data=machine_data,
            item_data=item_data,
            move_data=move_data,
            version_group_data=version_group_data
        )
    except (ValueError, HTTPError) as e:
        # Handle HTTP errors or other exceptions
        if isinstance(e, HTTPError) and e.response.status_code == 404:
            abort(404, description=f"Machine '{id_}' not found")
        else:
            logging.warning(f"Error occurred: {e}")
            return str(e), 500  # Internal Server Error for other issues


@pokemon_bp.route("/machine/page/<int:page>")
@pokemon_bp.route("/machine/", defaults={"page": 1})
def get_machines(page=1):
    try:
        per_page = 20  # Number of machines to display per page
        offset = (page - 1) * per_page
        url = f"https://pokeapi.co/api/v2/machine?offset={offset}&limit={per_page}"

        response = requests.get(url)
        if response.status_code != 200:
            abort(500, description="Failed to fetch machine data from the API")

        data = response.json()

        complete_machines = []

        # Process the results and extract the ID for each machine
        for machine in data['results']:
            machine_id = int(re.search(r'/(\d+)/$', machine['url']).group(1))
            machine_data = pokedex.APIResource.fetch_data("machine", machine_id)

            # Fetch related data: item, move, and version group
            item_data = pokedex.APIResource.fetch_data("item", machine_data['item']['name'])
            move_data = pokedex.APIResource.fetch_data("move", machine_data['move']['name'])
            version_group_data = pokedex.APIResource.fetch_data("version-group", machine_data['version_group']['name'])

            # Combine details into a single dictionary
            machine_detail = {
                'id': machine_id,
                'item': item_data,
                'move': move_data,
                'version_group': version_group_data
            }

            complete_machines.append(machine_detail)

        total_count = data['count']
        total_pages = (total_count + per_page - 1) // per_page

        return render_template("machine.html", data=complete_machines, page=page, total_pages=total_pages)
    except (ValueError, HTTPError) as e:
        # Handle HTTP errors or other exceptions
        if isinstance(e, HTTPError) and e.response.status_code == 404:
            abort(404, description=f"Machine endpoint failed")
        else:
            logging.warning(f"Error occurred: {e}")
            return str(e), 500  # Internal Server Error for other issues


@pokemon_bp.route("/move/", defaults={"id_or_name": None})
@pokemon_bp.route("/move/<id_or_name>")
@cache.cached(timeout=300)
def get_move(id_or_name):
    if id_or_name is None:
        # Fetch all moves
        url = "https://pokeapi.co/api/v2/move"
        data = fetch_all_results(url)
        return render_template("moves.html", data=data)
    else:
        try:
            # Fetch details for a specific move
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # If the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("move", id_or_name)

            if "name" not in data:
                abort(404, description=f"Pokemon Move '{id_or_name}' not found")

            pokemon_list = create_pokemon_list(data)

            # Check if the category data exists and is not None
            category = None
            if data.get("meta") and data["meta"].get("category"):
                category_name = data["meta"]["category"]["name"]
                category = pokedex.APIResource.fetch_data("move-category", category_name)
            else:
                logging.info(f"No category found for move {data['name']}")

            # Fetch Summary
            csv_file_path = get_path('move.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            summary_html = Markup(markdown.markdown(summary)) if summary else None

            return render_template("move_detail.html", data=data, category=category, pokemon_list=pokemon_list,
                                   summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_ailment/<id_or_name>")
@cache.cached(timeout=300)
def get_move_ailment(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("move-ailment", id_or_name)

        if "name" not in data:
            abort(404, description=f"Move Ailment '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_battle_style/<id_or_name>")
@cache.cached(timeout=300)
def get_move_battle_style(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("move-battle-style", id_or_name)

        if "name" not in data:
            abort(404, description=f"Move Battle Style '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_category/", defaults={"id_or_name": None})
@pokemon_bp.route("/move_category/<id_or_name>")
@cache.cached(timeout=300)
def get_move_category(id_or_name):
    try:
        if id_or_name is None:
            # Fetch all move categories
            url = "https://pokeapi.co/api/v2/move-category"
            data = fetch_all_results(url)
            return render_template("move_categories.html", data=data)
        else:
            # Fetch details for a specific move category
            category = pokedex.APIResource.fetch_data("move-category", id_or_name)

            if "name" not in category:
                abort(404, description=f"Move Category '{id_or_name}' not found")

            moves = []
            for move in category["moves"]:
                move_detail = pokedex.APIResource.fetch_data("move", move["name"])
                moves.append(move_detail)

            return render_template(
                "move_category_detail.html", category=category, moves=moves,
            )
    except Exception as e:
        return str(e), 404


@pokemon_bp.route("/move_damage_class/<id_or_name>")
@cache.cached(timeout=300)
def get_move_damage_class(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("move-damage-class", id_or_name)

        if "name" not in data:
            abort(404, description=f"Move Damage Class '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_learn_method/", defaults={"id_or_name": None})
@pokemon_bp.route("/move_learn_method/<id_or_name>")
@cache.cached(timeout=300)
def get_move_learn_method(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the move learn method list
        url = "https://pokeapi.co/api/v2/move-learn-method"
        data = fetch_all_results(url)
        return render_template("move_learn_methods.html", data=data)
    else:
        # id_or_name is provided, render the move learn method detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("move-learn-method", id_or_name)

            if "name" not in data:
                abort(404, description=f"Move Learn Method '{id_or_name}' not found")

            return render_template("move_learn_method_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_target/<id_or_name>")
@cache.cached(timeout=300)
def get_move_target(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("move-target", id_or_name)

        if "name" not in data:
            abort(404, description=f"Move Target '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/nature/<id_or_name>")
@cache.cached(timeout=300)
def get_nature(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("nature", id_or_name)

        if "name" not in data:
            abort(404, description=f"Nature '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pal_park_area/<id_or_name>")
@cache.cached(timeout=300)
def get_pal_park_area(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("pal-park-area", id_or_name)

        if "name" not in data:
            abort(404, description=f"Pal Park Area '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokeathlon_stat/<id_or_name>")
@cache.cached(timeout=300)
def get_pokeathlon_stat(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("pokeathlon-stat", id_or_name)

        if "name" not in data:
            abort(404, description=f"Pokeathlon '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokedex/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokedex/<id_or_name>")
@cache.cached(timeout=300)
def get_pokedex(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the list of Pokédexes
        url = "https://pokeapi.co/api/v2/pokedex"
        data = fetch_all_results(url)
        return render_template("pokedex.html", data=data)
    else:
        # id_or_name is provided, render the Pokédex detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("pokedex", id_or_name)

            if "name" not in data:
                abort(404, description=f"Pokedex '{id_or_name}' not found")

            pokemon_list = create_pokemon_list(data)
            return render_template("pokedex_detail.html", data=data, pokemon_list=pokemon_list)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route('/pokemon/')
def get_pokemon_list():
    page = request.args.get('page', 1, type=int)
    per_page = POKEMON_PER_PAGE
    offset = (page - 1) * per_page
    endpoint = f"{BASE_URL}/pokemon/?limit={per_page}&offset={offset}"

    response = requests.get(endpoint)
    data = response.json()

    pokemon_list = []

    # Fetch details for each Pokémon in the current set
    for pokemon in data["results"]:
        pokemon = pokedex.APIResource.fetch_data("pokemon", pokemon["name"])
        pokemon_list.append(pokemon)

    return render_template('pokemon_list.html', pokemon_list=pokemon_list, current_page=page)


@pokemon_bp.route("/pokemon/<id_or_name>")
@cache.cached(timeout=300)
def get_pokemon(id_or_name):
    csv_file_path = get_path('pokemon.csv')
    df = pd.read_csv(csv_file_path)

    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string

    try:
        data = pokedex.APIResource.fetch_data("pokemon", id_or_name)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status

    if not data or "name" not in data:
        abort(404, description=f"Pokemon '{id_or_name}' not found")

    data = {
        "name": data['name'].title(),
        "id": data["id"],
        "sprites": data["sprites"],
        "species": data["species"],
        "base_experience": data["base_experience"],
        "height": data["height"],
        "weight": data["weight"],
        "is_default": data["is_default"],
        "order": data["order"],
        "abilities": data.get("abilities", []),
        "moves": data.get("moves", []),
        "held_items": data.get("held_items", []),
        "types": data.get("types", []),
        "stats": data.get("stats", []),
    }

    # Categorize moves by how they're learned
    move_categories = {
        "level_up": [],
        "tm_hm": [],
        "breeding": [],
        "tutor": [],
        "other": [],
    }

    for move_detail in data.get("moves", []):
        move_learned_method = move_detail["version_group_details"][0]["move_learn_method"]["name"]
        move_data = {
            "name": move_detail["move"]["name"].replace("-", " ").title(),
            "url": url_for("pokemon.get_move", id_or_name=move_detail["move"]["name"]),
            "level_learned_at": move_detail["version_group_details"][0]["level_learned_at"]
        }

        if move_learned_method == "level-up":
            move_categories["level_up"].append(move_data)
        elif move_learned_method == "machine":
            move_categories["tm_hm"].append(move_data)
        elif move_learned_method == "egg":
            move_categories["breeding"].append(move_data)
        elif move_learned_method == "tutor":
            move_categories["tutor"].append(move_data)
        else:
            move_categories["other"].append(move_data)

    # Fetch and process type effectiveness
    type_effectiveness = {}
    for type_info in data["types"]:
        type_name = type_info["type"]["name"]
        type_data = pokedex.APIResource.fetch_data("type", type_name)
        damage_relations = type_data.get("damage_relations", {})
        type_effectiveness[type_name] = {
            "color": type_colors.get(type_name, "#FFFFFF"),  # Add color for the type
            "double_damage_to": [{"name": rel["name"], "color": type_colors.get(rel["name"], "#FFFFFF")} for rel in
                                 damage_relations.get("double_damage_to", [])],
            "half_damage_to": [{"name": rel["name"], "color": type_colors.get(rel["name"], "#FFFFFF")} for rel in
                               damage_relations.get("half_damage_to", [])],
            "no_damage_to": [{"name": rel["name"], "color": type_colors.get(rel["name"], "#FFFFFF")} for rel in
                             damage_relations.get("no_damage_to", [])],
            "double_damage_from": [{"name": rel["name"], "color": type_colors.get(rel["name"], "#FFFFFF")} for rel
                                   in damage_relations.get("double_damage_from", [])],
            "half_damage_from": [{"name": rel["name"], "color": type_colors.get(rel["name"], "#FFFFFF")} for rel in
                                 damage_relations.get("half_damage_from", [])],
            "no_damage_from": [{"name": rel["name"], "color": type_colors.get(rel["name"], "#FFFFFF")} for rel in
                               damage_relations.get("no_damage_from", [])],
        }

    # Try to fetch species data, but continue without it if it fails
    species_data = None
    try:
        species_data = pokedex.pokemon_species(data["id"])
    except requests.exceptions.HTTPError:
        logging.info(f"No species data found for Pokémon {data['name']}")

    # Get the sprite data and filter out null values and unwanted sprites
    sprites = {
        key: value
        for key, value in data["sprites"].items()
        if value is not None and key in valid_sprites
    }

    # Sort the sprites based on the desired order
    sorted_sprites = {key: sprites[key] for key in valid_sprites if key in sprites}

    # Initialize evolution_chain to None
    evolution_chain = None

    if species_data:
        # Build Evolution Chain only if species data is available
        evolution_id = pokedex.get_species_id_from_url(species_data['evolution_chain']['url'])

        # Using evolution_id get the chain
        evolution_chain_data = pokedex.evolution_chain(evolution_id)
        pokemon_name = evolution_chain_data["chain"]["species"]["name"]

        evolution_chain = pokedex.get_chain(evolution_chain_data, pokemon_name)

    # Retrieve the summary for the Pokémon
    summary = get_summary(data['name'], df)

    # Convert the markdown summary to HTML
    summary_html = Markup(markdown.markdown(summary)) if summary else None

    try:
        cards = get_pokemon_cards(data['name'])
    except Exception as e:
        # Log the exception and proceed with an empty list
        logging.warning(f"Error fetching cards for {data['name']}: {e}")
        cards = []

    return render_template(
        "pokemon_detail.html",
        data=data,
        species_data=species_data,
        sorted_sprites=sorted_sprites,
        evolution_chain=evolution_chain,
        type_effectiveness=type_effectiveness,
        move_categories=move_categories,
        summary_html=summary_html,
        cards=cards,
    )


@pokemon_bp.route("/pokemon_color/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon_color/<id_or_name>")
@cache.cached(timeout=300)
def get_pokemon_color(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the colors list
        url = "https://pokeapi.co/api/v2/pokemon-color"
        colors = fetch_all_results(url)
        return render_template("colors.html", colors=colors)
    else:
        # id_or_name is provided, render the color detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("pokemon-color", id_or_name)

            if "name" not in data:
                abort(404, description=f"Pokemon color '{id_or_name}' not found")

            # Use the create_pokemon_list function with the correct key
            pokemon_list = create_pokemon_list(data)

            return render_template("color_detail.html", data=data, pokemon_list=pokemon_list)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon_form/<id_or_name>")
def get_pokemon_form(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("pokemon-form", id_or_name)

        if "name" not in data:
            abort(404, description=f"Pokemon form '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon_habitat/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon_habitat/<id_or_name>")
@cache.cached(timeout=300)
def get_pokemon_habitat(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the habitats list
        url = "https://pokeapi.co/api/v2/pokemon-habitat"
        habitats = fetch_all_results(url)
        return render_template("habitats.html", habitats=habitats)
    else:
        # id_or_name is provided, render the habitat detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("pokemon-habitat", id_or_name)

            if "name" not in data:
                abort(404, description=f"Pokemon habitat '{id_or_name}' not found")

            # Use the create_pokemon_list function with the correct key
            pokemon_list = create_pokemon_list(data)

            return render_template("habitat_detail.html", data=data, pokemon_list=pokemon_list)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon_shape/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon_shape/<id_or_name>")
@cache.cached(timeout=300)
def get_pokemon_shape(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the shapes list
        url = "https://pokeapi.co/api/v2/pokemon-shape"
        types = fetch_all_results(url)
        return render_template("shapes.html", types=types)
    else:
        # id_or_name is provided, render the shape detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string
        try:
            data = pokedex.APIResource.fetch_data("pokemon-shape", id_or_name)

            if "name" not in data:
                abort(404, description=f"Pokemon shape '{id_or_name}' not found")

            pokemon_list = create_pokemon_list(data)
            return render_template("shape_detail.html", data=data, pokemon_list=pokemon_list)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon_species/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon_species/<id_or_name>")
@cache.cached(timeout=300)
def get_pokemon_species(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the Pokémon species list
        url = "https://pokeapi.co/api/v2/pokemon-species"
        data = fetch_all_results(url)
        return render_template("pokemon_species.html", data=data)
    else:
        # id_or_name is provided, render the species detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            def get_evolution_chain(val):
                params = val["url"].split("/")[-3:-1]
                params[1] = int(params[1])
                return params

            data = pokedex.APIResource.fetch_data("pokemon-species", id_or_name,
                                                  custom={"evolution_chain": get_evolution_chain})

            # Use the create_pokemon_list function with the correct key
            pokemon_list = create_pokemon_list(data)

            if "name" not in data:
                abort(404, description=f"Pokemon species '{id_or_name}' not found")

            return render_template("pokemon_species_detail.html", data=data, pokemon_list=pokemon_list)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/region/", defaults={"id_or_name": None})
@pokemon_bp.route("/region/<id_or_name>")
@cache.cached(timeout=300)
def get_region(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the regions list
        url = "https://pokeapi.co/api/v2/region"
        data = fetch_all_results(url)
        return render_template("regions.html", data=data)
    else:
        # id_or_name is provided, render the region detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("region", id_or_name)

            if "name" not in data:
                abort(404, description=f"Region '{id_or_name}' not found")

            # Fetch Summary
            csv_file_path = get_path('region.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template("region_detail.html", data=data, summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/stat/<id_or_name>")
def get_stat(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("stat", id_or_name)

        if "name" not in data:
            abort(404, description=f"Stat '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/super_contest_effect/<int:id_>")
def get_super_contest_effect(id_):
    try:
        data = pokedex.APIResource.fetch_data("super-contest-effect", id_)

        if "id" not in data:
            abort(404, description=f"Super Contest Effect '{id_}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status
    except HTTPError as e:
        # If the HTTP error is 404, raise a 404 Not Found
        if e.response.status_code == 404:
            abort(404, description=f"Super Contest Effect '{id_}' not found")
        else:
            # For other HTTP errors, you might want to log them or handle differently
            logging.warning(f"HTTP error occurred: {e}")
            return str(e), e.response.status_code


@pokemon_bp.route("/type/", defaults={"id_or_name": None})
@pokemon_bp.route("/type/<id_or_name>")
@cache.cached(timeout=300)
def get_type(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the types list
        url = "https://pokeapi.co/api/v2/type"
        types = fetch_all_results(url)
        return render_template("types.html", types=types)
    else:
        # id_or_name is provided, render the type detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("type", id_or_name)

            if "name" not in data:
                abort(404, description=f"Pokemon type '{id_or_name}' not found")

            pokemon_list = create_pokemon_list(data)

            # Fetch Summary
            csv_file_path = get_path('type.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template(
                "type_detail.html",
                type_effectiveness=data,
                pokemon_list=pokemon_list,
                type_colors=type_colors,
                summary_html=summary_html,
            )
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/version/", defaults={"id_or_name": None})
@pokemon_bp.route("/version/<id_or_name>")
@cache.cached(timeout=300)
def get_version(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the versions list
        url = "https://pokeapi.co/api/v2/version"
        data = fetch_all_results(url)
        return render_template("versions.html", data=data)
    else:
        # id_or_name is provided, render the version detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("version", id_or_name)

            if "name" not in data:
                abort(404, description=f"Version '{id_or_name}' not found")

            # Fetch Summary
            csv_file_path = get_path('version.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template("version_detail.html", data=data, summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/version_group/", defaults={"id_or_name": None})
@pokemon_bp.route("/version_group/<id_or_name>")
@cache.cached(timeout=300)
def get_version_group(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the version groups list
        url = "https://pokeapi.co/api/v2/version-group"
        data = fetch_all_results(url)
        return render_template("version_groups.html", data=data)
    else:
        # id_or_name is provided, render the version group detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("version-group", id_or_name)
            if "name" not in data:
                abort(404, description=f"Version Group '{id_or_name}' not found")

            # Fetch Summary
            csv_file_path = get_path('version-group.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template("version_group_detail.html", data=data, summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/<api_endpoint>/<id_or_name>")
def get_endpoint_data(api_endpoint, id_or_name):
    try:
        # Convert the endpoint from hyphenated form to underscore form
        endpoint_pythonic = api_endpoint.replace('-', '_')

        # Check if id_or_name can be converted to an integer
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        # Check if the function exists in the __all__ list
        if endpoint_pythonic in pokedex.__all__:
            func = getattr(sys.modules[__name__], endpoint_pythonic)  # get the function from current module by its name
            data = func(id_or_name)
            return render_template("generic.html", data=data)
        else:
            raise ValueError(f"No such endpoint: {api_endpoint}")
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/webhook/", methods=["POST", "GET"])
def webhook():
    secret = os.getenv('WEBHOOK_SECRET')

    if request.method == "POST":

        # Verify the webhook secret is set
        if secret is None:
            logging.error("Webhook secret is not configured")
            abort(500, 'Webhook secret is not configured')

        # Verify the signature from GitHub
        signature = request.headers.get('X-Hub-Signature-256')
        if signature is None:
            logging.error("No signature provided")
            abort(403, 'No signature provided')

        sha_name, signature_from_github = signature.split('=')
        if sha_name != 'sha256':
            logging.error(f"Signature type '{sha_name}' is not supported")
            abort(501, 'Signature type not supported')

        # Calculate the expected signature
        mac = hmac.new(bytes(secret, 'utf-8'), msg=request.data, digestmod=hashlib.sha256)
        generated_signature = mac.hexdigest()

        # Compare the generated signature with the one from GitHub
        if not hmac.compare_digest(generated_signature, signature_from_github):
            logging.error("Invalid signature - Signatures do not match")
            abort(403, 'Invalid signature')

        # Pull the latest changes from the repository
        try:
            result = subprocess.run(
                ["git", "-C", "/var/www/pokeAPI", "pull"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logging.info("Git pull output: " + result.stdout)
        except subprocess.CalledProcessError as e:
            logging.error(f"Git pull failed: {e.stderr}")
            abort(500, f'Git pull failed: {str(e)}')

        # Log the command being run
        logging.info("Attempting to restart Gunicorn with sudo")

        # Restart Gunicorn using sudo with timeout
        try:
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', 'gunicorn'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30  # Timeout after 30 seconds
            )
            logging.info(f"Gunicorn restart output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Gunicorn restart failed with return code {e.returncode}: {e.stderr}")
            abort(500, f'Gunicorn restart failed: {str(e)}')
        except subprocess.TimeoutExpired as e:
            logging.error(f"Gunicorn restart timed out: {e}")
            abort(500, 'Gunicorn restart timed out.')

        return 'Success', 200

    elif request.method == "GET":
        logging.info("GET request received - Returning 403 Forbidden")
        return render_template('403.html'), 403

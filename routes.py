import logging
import math
import requests
from flask import Blueprint, render_template, request

from pokedex import models, utils

pokemon_bp = Blueprint(
    "pokemon", __name__, template_folder="templates", static_folder="static"
)

BASE_URL = "https://pokeapi.co/api/v2"
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites"


@pokemon_bp.route("/")
@utils.cache.cached(timeout=50)
def index():
    logging.info(
        "Inside index() function"
    )  # This line will print a message to the console whenever the function is called

    db = utils.get_db()
    collection = db["pokemon"]

    page = int(
        request.args.get("page", 1)
    )  # Get the current page number from the query parameters
    limit = 20  # Number of items per page

    # Calculate the offset based on the current page number and limit
    offset = (page - 1) * limit

    total_pokemons = collection.count_documents(
        {}
    )  # Total number of pokemons in the collection
    total_pages = math.ceil(
        total_pokemons / limit
    )  # Calculate the total number of pages

    # Get the pokemons for the current page using the offset and limit
    pokemons = collection.find().skip(offset).limit(limit)
    pokemons = list(pokemons)

    next_page = (
        page + 1 if page < total_pages else None
    )  # Calculate the next page number
    prev_page = page - 1 if page > 1 else None  # Calculate the previous page number

    next_url = (
        f"/?page={next_page}" if next_page else None
    )  # Construct the next page URL
    prev_url = (
        f"/?page={prev_page}" if prev_page else None
    )  # Construct the previous page URL

    return render_template(
        "pokemon.html", pokemons=pokemons, next_url=next_url, prev_url=prev_url
    )


@pokemon_bp.route("/pokemon/<id_or_name>")
def get_pokemon(id_or_name):
    data = models.pokemon_detail(id_or_name)

    if data is not None:
        data = {
            "name": data["name"].title(),
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
        }
        print(data.get("held_items", []))
        species_data = models.pokemon_species(data["id"])
        #logging.info(f"species_data: {species_data}")

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

        # Get the sprite data and filter out null values and unwanted sprites
        sprites = {
            key: value
            for key, value in data["sprites"].items()
            if value is not None and key in valid_sprites
        }

        # Sort the sprites based on the desired order
        sorted_sprites = {key: sprites[key] for key in valid_sprites if key in sprites}

        # Build Evolution Chain

        evolution_id = models.get_species_id_from_url(species_data['evolution_chain']['url'])

        # Using evolution_id get the chain
        evolution_chain_data = models.evolution_chain(evolution_id)
        pokemon_name = evolution_chain_data["chain"]["species"]["name"]
        #logging.info(f"name being fed to chain: {pokemon_name}")
        evolution_chain = models.get_chain(evolution_chain_data, pokemon_name)

        return render_template(
            "pokemon_detail.html",
            data=data,
            species_data=species_data,
            sorted_sprites=sorted_sprites,
            evolution_chain=evolution_chain,
        )
    else:
        return "Pokemon not found", 404


@pokemon_bp.route("/ability/<int:id_>")
@utils.cache.cached(timeout=50)
def get_ability_data(id_):
    response = requests.get(f"{BASE_URL}/ability/{id_}")
    if response.status_code == 200:
        data = response.json()

        return render_template("pokemon_ability.html", data=data)
    else:
        return "Ability not found", 404


@pokemon_bp.route("/move/<int:id_or_name>")
@utils.cache.cached(timeout=50)
def get_move_data(id_or_name):
    try:
        data = models.APIResource.fetch_data("move", id_or_name)
        logging.info("Move data: {data}")
        return render_template("pokemon_item.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


'''
@pokemon_bp.route("/item/<id_or_name>")
@utils.cache.cached(timeout=50)
def get_item_data(id_or_name):
    response = requests.get(f"{BASE_URL}/item/{id_or_name}")
    if response.status_code == 200:
        data = response.json()
        data = models.filter_english_data(data)
        return render_template("pokemon_item.html", data=data)
    else:
        return "Item not found", 404
'''


@pokemon_bp.route("/pokemon/<id_or_name>/encounters")
@utils.cache.cached(timeout=50)
def get_encounter_data(id_or_name):
    logging.info("Accessing encounters for: {id_or_name}")
    response = requests.get(
        f"{BASE_URL}/{id_or_name}/encounters/"
    )
    logging.info(f"Response from PokeAPI: {response.status_code}")

    if response.status_code == 200:
        data = response.json()

        return render_template("pokemon_encounter.html", data=data)
    else:
        return "Encounter not found", 404


@pokemon_bp.route("/species/<id_or_name>")
@utils.cache.cached(timeout=50)
def get_species_data(id_or_name):
    response = requests.get(f"{BASE_URL}/pokemon-species/{id_or_name}")
    logging.info(response)
    if response.status_code == 200:
        data = response.json()

        return render_template("pokemon_species.html", data=data)
    else:
        return "Species not found", 404


@pokemon_bp.route("/item/<int:id_or_name>")
@utils.cache.cached(timeout=50)
def get_item_data(id_or_name):
    try:
        data = models.APIResource.fetch_data("item", id_or_name)
        return render_template("pokemon_item.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokedex/<int:id_or_name>")
@utils.cache.cached(timeout=50)
def get_pokedex_data(id_or_name):
    try:
        data = models.pokedex(id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item-category/<int:id_or_name>")
@utils.cache.cached(timeout=50)
def get_item_category_data(id_or_name):
    try:
        data = models.item_category(id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/<api_endpoint>/<id_or_name>")
@utils.cache.cached(timeout=50)
def get_endpoint_data(api_endpoint, id_or_name):
    try:
        # Convert the endpoint from hyphenated form to underscore form
        endpoint_pythonic = api_endpoint.replace('-', '_')

        # Check if id_or_name can be converted to an integer
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string
        print(f"id_or_name: {id_or_name}, Type: {type(id_or_name)}")

        # Check if the function exists in the models module
        if hasattr(models, endpoint_pythonic):
            func = getattr(models, endpoint_pythonic)  # get the function from models by its name
            data = func(id_or_name)
            return render_template("generic.html", data=data)
        else:
            raise ValueError(f"No such endpoint: {api_endpoint}")
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status



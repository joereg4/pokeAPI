import logging

from flask import Blueprint, render_template, request, g
from pokedex.models.pokemon import Pokemon
from pokedex.models.utils import get_evolution_chain, filter_english_data
from pokedex.utils.db_utils import get_db, close_db
import requests
import math

logging.basicConfig(level=logging.INFO)

pokemon_bp = Blueprint(
    "pokemon", __name__, template_folder="templates", static_folder="static"
)

pokeapi_base_url = "https://pokeapi.co/api/v2/"


@pokemon_bp.route("/")
def index():
    logging.info(
        "Inside index() function"
    )  # This line will print a message to the console whenever the function is called

    db = get_db()
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


@pokemon_bp.route("/pokemon/<name>")
def get_pokemon(name):
    db = get_db()
    collection = db["pokemon"]

    pokemon = collection.find_one({"name": name.lower()})
    if pokemon is not None:
        data = {
            "name": pokemon["name"].title(),
            "id": pokemon["id"],
            "sprites": pokemon["sprites"],
            "species": pokemon["species"],
            "base_experience": pokemon["base_experience"],
            "height": pokemon["height"],
            "weight": pokemon["weight"],
            "is_default": pokemon["is_default"],
            "order": pokemon["order"],
            "abilities": pokemon.get("abilities", []),
            "moves": pokemon.get("moves", []),
            "held_items": pokemon.get("held_items", []),
        }

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
            for key, value in pokemon["sprites"].items()
            if value is not None and key in valid_sprites
        }

        # Sort the sprites based on the desired order
        sorted_sprites = {key: sprites[key] for key in valid_sprites if key in sprites}

        # Get the evolution chain using the species url
        species_id = (
            pokemon["species"]["url"]
            .replace("https://pokeapi.co/api/v2/pokemon-species/", "")
            .strip("/")
        )
        evolution_chain, species_data = get_evolution_chain(species_id)

        return render_template(
            "pokemon_detail.html",
            data=data,
            sprites=sorted_sprites,
            evolution_chain=evolution_chain,
            species_data=species_data,
        )
    else:
        return "Pokemon not found", 404


@pokemon_bp.route("/ability/<int:ability_id>")
def get_ability_data(ability_id):
    response = requests.get(f"https://pokeapi.co/api/v2/ability/{ability_id}")
    if response.status_code == 200:
        data = response.json()

        # Filter for English language data
        data = filter_english_data(data)

        return render_template("pokemon_ability.html", data=data)
    else:
        return "Ability not found", 404


@pokemon_bp.route("/move/<int:move_id>")
def get_move_data(move_id):
    response = requests.get(f"https://pokeapi.co/api/v2/move/{move_id}")
    if response.status_code == 200:
        data = response.json()
        return render_template("pokemon_move.html", data=data)
    else:
        return "Move not found", 404


@pokemon_bp.route("/item/<id_or_name>")
def get_item_data(id_or_name):
    response = requests.get(f"https://pokeapi.co/api/v2/item/{id_or_name}")
    if response.status_code == 200:
        data = response.json()

        # Filter for English language data
        data = filter_english_data(data)

        return render_template("pokemon_item.html", data=data)
    else:
        return "Item not found", 404


@pokemon_bp.route("/pokemon/<id_or_name>/encounters")
def get_encounter_data(id_or_name):
    logging.info("Accessing encounters for: {id_or_name}")
    response = requests.get(
        f"https://pokeapi.co/api/v2/pokemon/{id_or_name}/encounters/"
    )
    logging.info(f"Response from PokeAPI: {response.status_code}")

    if response.status_code == 200:
        data = response.json()

        return render_template("pokemon_encounter.html", data=data)
    else:
        return "Encounter not found", 404


@pokemon_bp.route("/species/<id_or_name>")
def get_species_data(id_or_name):
    response = requests.get(f"https://pokeapi.co/api/v2/pokemon-species/{id_or_name}")
    logging.info(f"https://pokeapi.co/api/v2/pokemon-species/{id_or_name}")
    if response.status_code == 200:
        data = response.json()

        data = filter_english_data(data)

        return render_template("pokemon_species.html", data=data)
    else:
        return "Species not found", 404


@pokemon_bp.route("/<api_endpoint>/<int:id>")
def get_endpoint_data(api_endpoint, id):
    full_url = f"{pokeapi_base_url}/{api_endpoint}/{id}"
    response = requests.get(full_url)

    if response.status_code == 200:
        data = response.json()

        # Filter for English language data if 'effect_entries' field exists
        data = filter_english_data(data)

        return render_template("generic.html", data=data)
    else:
        return "Endpoint not found", 404

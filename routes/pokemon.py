# routes/pokemon.py
import logging
import markdown
import pandas as pd
import requests
from flask import Blueprint, render_template, abort, url_for, request
from markupsafe import Markup

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results, create_pokemon_list, get_summary, get_path, get_pokemon_cards
from pokedex.utils import Config

pokemon_bp = Blueprint("pokemon", __name__, template_folder="templates", static_folder="static")

BASE_URL = Config.BASE_URL
POKEMON_PER_PAGE = Config.POKEMON_PER_PAGE
ITEMS_PER_PAGE = Config.ITEMS_PER_PAGE
VALID_SPRITES = Config.VALID_SPRITES
TYPE_COLORS = Config.TYPE_COLORS


@pokemon_bp.route("/")
def index():
    pokedex.load_resources()  # Load resources from the CSV
    # Fetch total Pokémon count
    pokemon_count_response = requests.get(f"{BASE_URL}/pokemon?limit=1")
    pokemon_count = pokemon_count_response.json()["count"]

    # Fetch total types count
    types_count_response = requests.get(f"{BASE_URL}/type?limit=1")
    types_count = types_count_response.json()["count"]

    return render_template(
        "index.html",
        pokemon_count=pokemon_count,
        types_count=types_count,
    )


@pokemon_bp.route("/detective-pikachu")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_detective_pikachu_pokemon():
    # List of Pokémon featured in the Detective Pikachu movie
    detective_pikachu_pokemon = [
        "pikachu", "psyduck", "mewtwo", "charmander", "charizard", "greninja", "mr-mime",
        "bulbasaur", "jigglypuff", "ditto", "eevee", "flareon", "snubbull", "torterra",
        "aipom", "cubone", "pancham", "pangoro", "gengar", "machamp", "lickitung", "growlithe",
        "slaking", "morelull", "rufflet", "pidgeot", "pidgey", "emolga", "dodrio",
        "magikarp", "gyarados", "treecko", "rattata", "kingler", "squirtle", "ludicolo",
        "loudred", "comfey", "blastoise", "arcanine", "sneasel", "venusaur", "purrloin",
        "braviary"
    ]

    # Transform the list into the expected format
    data = {
        "detective": [{"pokemon": {"name": name}} for name in detective_pikachu_pokemon]
    }

    # Create the Pokémon list from the predefined list of Pokémon names
    pokemon_list = create_pokemon_list(data)

    # Render a template for the Detective Pikachu Pokémon
    return render_template("detective_pikachu.html", pokemon_list=pokemon_list)


@pokemon_bp.route("/pokedex/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokedex/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_pokedex(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the list of Pokédexes
        url = f"{BASE_URL}/pokedex"
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
@cache.cached(timeout=Config.CACHE_TIMEOUT)
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
            "url": url_for("abilities_moves_items.get_move", id_or_name=move_detail["move"]["name"]),
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
            "color": TYPE_COLORS.get(type_name, "#FFFFFF"),  # Add color for the type
            "double_damage_to": [{"name": rel["name"], "color": TYPE_COLORS.get(rel["name"], "#FFFFFF")} for rel in
                                 damage_relations.get("double_damage_to", [])],
            "half_damage_to": [{"name": rel["name"], "color": TYPE_COLORS.get(rel["name"], "#FFFFFF")} for rel in
                               damage_relations.get("half_damage_to", [])],
            "no_damage_to": [{"name": rel["name"], "color": TYPE_COLORS.get(rel["name"], "#FFFFFF")} for rel in
                             damage_relations.get("no_damage_to", [])],
            "double_damage_from": [{"name": rel["name"], "color": TYPE_COLORS.get(rel["name"], "#FFFFFF")} for rel
                                   in damage_relations.get("double_damage_from", [])],
            "half_damage_from": [{"name": rel["name"], "color": TYPE_COLORS.get(rel["name"], "#FFFFFF")} for rel in
                                 damage_relations.get("half_damage_from", [])],
            "no_damage_from": [{"name": rel["name"], "color": TYPE_COLORS.get(rel["name"], "#FFFFFF")} for rel in
                               damage_relations.get("no_damage_from", [])],
        }

    # Try to fetch species data, but continue without it if it fails
    species_data = None
    try:
        species_data = pokedex.APIResource.fetch_data("pokemon-species", data["species"]["name"])
    except requests.exceptions.HTTPError:
        logging.debug(f"No species data found for Pokémon {data['name']}")

    # Get the sprite data and filter out null values and unwanted sprites
    sprites = {
        key: value
        for key, value in data["sprites"].items()
        if value is not None and key in VALID_SPRITES
    }

    # Sort the sprites based on the desired order
    sorted_sprites = {key: sprites[key] for key in VALID_SPRITES if key in sprites}

    # Initialize evolution_chain to None
    evolution_chain = None

    if species_data:
        # Check if the evolution_chain key exists before attempting to access it
        if 'evolution_chain' in species_data and 'url' in species_data['evolution_chain']:
            evolution_id = pokedex.get_species_id_from_url(species_data['evolution_chain']['url'])

            # Using evolution_id get the chain
            evolution_chain_data = pokedex.APIResource.fetch_data("evolution-chain", evolution_id)
            pokemon_name = evolution_chain_data["chain"]["species"]["name"]

            evolution_chain = pokedex.get_chain(evolution_chain_data, pokemon_name)
        else:
            logging.debug(f"No evolution chain found for Pokémon with ID {id_or_name}")
            evolution_chain = None

    # Retrieve the summary for the Pokémon
    summary = get_summary(data['name'], df)

    # Convert the markdown summary to HTML
    summary_html = Markup(markdown.markdown(summary)) if summary else None

    try:
        cards = get_pokemon_cards(data['name'])
    except Exception as e:
        # Log the exception and proceed with an empty list
        logging.debug(f"Error fetching cards for {data['name']}: {e}")
        cards = []

    # Check for Official Artwork
    try:
        entry_number = species_data.get('pokedex_numbers', [{}])[0].get('entry_number', None)
        official_artwork = data.get('sprites', {}).get('other', {}).get('official-artwork', {}).get('front_default')
        official_artwork = pokedex.get_official_artwork(data['name'], official_artwork, entry_number)
    except Exception as e:
        logging.debug(f"Error identifying entry number and official artwork for {data['name']}: {e}")
        official_artwork = None

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
        official_artwork=official_artwork,
    )


@pokemon_bp.route("/pokemon-color/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon-color/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_pokemon_color(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the colors list
        url = f"{BASE_URL}/pokemon-color"
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

            # Process the list of Pokémon
            pokemon_list = pokedex.PokemonList(data).create_pokemon_list()

            return render_template("color_detail.html", data=data, pokemon_list=pokemon_list)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon-form/<id_or_name>")
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


@pokemon_bp.route("/pokemon-habitat/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon-habitat/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_pokemon_habitat(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the habitats list
        url = f"{BASE_URL}/pokemon-habitat"
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


@pokemon_bp.route("/pokemon-shape/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon-shape/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_pokemon_shape(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the shapes list
        url = f"{BASE_URL}/pokemon-shape"
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


@pokemon_bp.route("/pokemon-species/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon-species/<id_or_name>")
def get_pokemon_species(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the Pokémon species list
        url = f"{BASE_URL}/pokemon-species"
        data = fetch_all_results(url)
        return render_template("pokemon_species.html", data=data)
    else:
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("pokemon-species", id_or_name)

            # Extract only the relevant data for the Pokémon list
            simplified_data = {
                "pokemon_species": [
                    {
                        "name": data.get("name")
                    }
                ]
            }

            # Process the list of Pokémon
            pokemon_list = pokedex.PokemonList(simplified_data).create_pokemon_list()

            return render_template("pokemon_species_detail.html", data=data, pokemon_list=pokemon_list)
        except ValueError as e:
            logging.error(f"ValueError in fetching species {id_or_name}: {e}")
            return str(e), 400  # Return the error message with a 400 Bad Request status
        except Exception as e:
            logging.error(f"Unexpected error occurred: {e}")
            return str(e), 500  # Return a generic server error


@pokemon_bp.route("/type/", defaults={"id_or_name": None})
@pokemon_bp.route("/type/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_type(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the types list
        url = f"{BASE_URL}/type"
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
                type_colors=TYPE_COLORS,
                summary_html=summary_html,
            )
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status

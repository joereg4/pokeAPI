import logging
from flask import Blueprint, render_template, request, json, current_app, url_for
from cache import cache
import requests
import pokedex
import sys

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


def create_pokemon_list(data):
    try:
        # If data is a list, assume it contains the Pokémon entries directly
        if isinstance(data, list):
            pokemon_entries = data
        else:
            # Possible keys that might contain the Pokémon species list
            possible_keys = ["pokemon", "pokemon_species", "pokemon_entries"]

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
                print(f"Warning: Invalid Pokémon entry structure: {pokemon_entry}")
                continue

            if not pokemon_name:
                print(f"Warning: Could not find Pokémon name in entry: {pokemon_entry}")
                continue

            # Fetch the Pokémon data
            pokemon = pokedex.APIResource.fetch_data("pokemon", pokemon_name)

            # Check if the 'sprites' key exists in the Pokémon data
            if "sprites" in pokemon:
                pokemon_list.append(pokemon)
            else:
                print(f"Warning: No sprites found for Pokémon {pokemon_name}")

        return pokemon_list
    except ValueError as e:
        print(f"Error fetching Pokémon data: {e}")
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
    return render_template(
        "index.html",
        pokemon_count=pokemon_count,
        types_count=types_count,
        abilities_count=abilities_count,
        color_count=color_count,
        habitat_count=habitat_count,
    )


@pokemon_bp.route("/abilities")
@cache.cached(timeout=300)
def get_abilities_list():
    url = "https://pokeapi.co/api/v2/ability"
    abilities = fetch_all_results(url)
    return render_template("abilities.html", abilities=abilities)


@pokemon_bp.route("/ability/<id_or_name>")
def get_ability(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("ability", id_or_name)
        return render_template("ability.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/berry/<id_or_name>")
def get_berry(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("berry", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/berry_firmness/<id_or_name>")
def get_berry_firmness(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("berry-firmness", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/berry_flavor/<id_or_name>")
def get_berry_flavor(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("berry-flavor", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/characteristic/<int:id_>")
def get_characteristic(id_):
    try:
        data = pokedex.APIResource.fetch_data("characteristic", id_)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/colors")
@cache.cached(timeout=300)
def get_colors_list():
    url = "https://pokeapi.co/api/v2/pokemon-color"
    colors = fetch_all_results(url)
    return render_template("colors.html", colors=colors)


@pokemon_bp.route("/contest_effect/<int:id_>")
def get_contest_effect(id_):
    try:
        data = pokedex.APIResource.fetch_data("contest-effect", id_)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/contest_type/<id_or_name>")
def get_contest_type(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("contest-type", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/egg_group/<id_or_name>")
def get_egg_group(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string

    try:
        data = pokedex.APIResource.fetch_data("egg-group", id_or_name)
        if not data:
            return "No data found", 404  # Handle case where no data is returned

        # Use the create_pokemon_list function with the correct key
        pokemon_list = create_pokemon_list(data)

        return render_template("egg_group_detail.html", data=data, pokemon_list=pokemon_list)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/encounter_condition/<id_or_name>")
def get_encounter_condition(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("encounter-condition", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/encounter_condition_value/<id_or_name>")
def get_encounter_condition_value(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("encounter-condition-value", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/encounter_method/<id_or_name>")
def get_encounter_method(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("encounter-method", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/evolution_chain/<int:id_>")
def get_evolution_chain(id_):
    try:
        data = pokedex.APIResource.fetch_data("evolution-chain", id_)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/evolution_trigger/<id_or_name>")
def get_evolution_trigger(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("evolution-trigger", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/gender/<id_or_name>")
def get_gender(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("gender", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/generation/<id_or_name>")
def get_generation(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("generation", id_or_name)

        # Use the create_pokemon_list function with the correct key
        pokemon_list = create_pokemon_list(data)

        return render_template("generation_detail.html", data=data, pokemon_list=pokemon_list)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/growth_rate/<id_or_name>")
def get_growth_rate(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("growth-rate", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/habitats")
@cache.cached(timeout=300)
def get_habitats_list():
    url = "https://pokeapi.co/api/v2/pokemon-habitat"
    habitats = fetch_all_results(url)
    return render_template("habitats.html", habitats=habitats)


@pokemon_bp.route("/item/<id_or_name>")
@cache.cached(timeout=300)
def get_item(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("item", id_or_name)
        return render_template("item.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item_attribute/<id_or_name>")
def get_item_attribute(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("item-attribute", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item_category/<id_or_name>")
def get_item_category(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("item-category", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item_fling_effect/<id_or_name>")
def get_item_fling_effect(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("item-fling-effect", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item_pocket/<id_or_name>")
def get_item_pocket(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("item-pocket", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/language/<id_or_name>")
def get_language(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("language", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/location/<id_or_name>")
def get_location(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("location", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/location_area/<id_or_name>")
def get_location_area(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("location-area", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/machine/<int:id_>")
def get_machine(id_):
    try:
        data = pokedex.APIResource.fetch_data("machine", id_)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move/<id_or_name>")
@cache.cached(timeout=300)
def get_move(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("move", id_or_name)

        # Fetch additional details for the move
        category = pokedex.APIResource.fetch_data("move-category", data["meta"]["category"]["name"])

        return render_template("move_detail.html", data=data, category=category, )
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_ailment/<id_or_name>")
def get_move_ailment(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("move-ailment", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_battle_style/<id_or_name>")
def get_move_battle_style(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("move-battle-style", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_category/<id_or_name>")
@cache.cached(timeout=300)
def get_move_category(id_or_name):
    try:
        category = pokedex.APIResource.fetch_data("move-category", id_or_name)
        # Optionally, fetch each move's detailed data if needed
        moves = []
        for move in category["moves"]:
            move_detail = pokedex.APIResource.fetch_data("move", move["name"])
            moves.append(move_detail)

        return render_template(
            "move_category_detail.html", category=category, moves=moves,
        )
    except Exception as e:
        return str(e), 404


@pokemon_bp.route("/move_category_list/")
@cache.cached(timeout=300)
def get_move_category_list():
    try:
        # Fetch the full list of move categories
        response = requests.get("https://pokeapi.co/api/v2/move-category/")
        category_list = response.json()

        return render_template(
            "move_category.html", category_list=category_list["results"],
        )
    except Exception as e:
        return str(e), 404


@pokemon_bp.route("/move_damage_class/<id_or_name>")
def get_move_damage_class(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("move-damage-class", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_learn_method/<id_or_name>")
def get_move_learn_method(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("move-learn-method", id_or_name)
        return render_template("move_learn_method_detail.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_target/<id_or_name>")
def get_move_target(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("move-target", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/nature/<id_or_name>")
def get_nature(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("nature", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pal_park_area/<id_or_name>")
def get_pal_park_area(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("pal-park-area", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokeathlon_stat/<id_or_name>")
def get_pokeathlon_stat(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("pokeathlon-stat", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokedex/<id_or_name>")
# @cache.cached(timeout=300)
def get_pokedex(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string

    try:
        data = pokedex.APIResource.fetch_data("pokedex", id_or_name)
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
    cache.set(cache_key, rendered_template, timeout=300)


# @pokemon_bp.route('/pokemon/')
# @cache.cached(timeout=300)
# def get_pokemon_list():
#     try:
#         url = "https://pokeapi.co/api/v2/pokemon"
#         data = fetch_all_results(url)
#         pokemon_list = create_pokemon_list(data)
#
#         return render_template('pokemon_list.html', pokemon_list=pokemon_list)
#     # cache.set(cache_key, rendered_template, timeout=300)
#     except ValueError as e:
#         return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon/<id_or_name>")
# @cache.cached(timeout=300)
def get_pokemon(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string

    try:
        def get_location_area_encounters(val):
            params = val.split("/")[-3:]
            params[1] = int(params[1])
            print(f"Encounters Parms: {params}")
            return params

        data = pokedex.APIResource.fetch_data("pokemon", id_or_name, )

    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status

    if data is not None:
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
        print(f"Move Level Data: {move_categories}")

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
            print(f"Warning: No species data found for Pokémon {data['name']}")

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

            # logging.info(f"name being fed to chain: {pokemon_name}")
            evolution_chain = pokedex.get_chain(evolution_chain_data, pokemon_name)

        return render_template(
            "detail.html",
            data=data,
            species_data=species_data,
            sorted_sprites=sorted_sprites,
            evolution_chain=evolution_chain,
            type_effectiveness=type_effectiveness,
            move_categories=move_categories,
        )
    else:
        return "Pokemon not found", 404


@pokemon_bp.route("/pokemon_color/<id_or_name>")
@cache.cached(timeout=300)
def get_pokemon_color(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string

    try:
        data = pokedex.APIResource.fetch_data("pokemon-color", id_or_name)
        if not data:
            return "No data found", 404  # Handle case where no data is returned

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
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon_habitat/<id_or_name>")
@cache.cached(timeout=300)
def get_pokemon_habitat(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string

    try:
        data = pokedex.APIResource.fetch_data("pokemon-habitat", id_or_name)
        if not data:
            return "No data found", 404  # Handle case where no data is returned

        # Use the create_pokemon_list function with the correct key
        pokemon_list = create_pokemon_list(data)

        return render_template("habitat_detail.html", data=data, pokemon_list=pokemon_list)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon_shape/<id_or_name>")
def get_pokemon_shape(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("pokemon-shape", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon_species/<id_or_name>")
def get_pokemon_species(id_or_name):
    # Check if id_or_name can be converted to an integer
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
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/region/<id_or_name>")
def get_region(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("region", id_or_name)
        return render_template("region_detail.html", data=data)
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
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/super_contest_effect/<int:id_>")
def get_super_contest_effect(id_):
    try:
        data = pokedex.APIResource.fetch_data("super-contest-effect", id_)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/type/<id_or_name>")
@cache.cached(timeout=300)
def get_type(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string

    try:
        data = pokedex.APIResource.fetch_data("type", id_or_name)
        pokemon_list = create_pokemon_list(data)

        return render_template(
            "type_detail.html",
            data=data,
            pokemon_list=pokemon_list,
            type_colors=type_colors
        )
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/types")
@cache.cached(timeout=300)
def get_types_list():
    url = "https://pokeapi.co/api/v2/type"
    types = fetch_all_results(url)
    return render_template("types.html", types=types)


@pokemon_bp.route("/version/<id_or_name>")
def get_version(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("version", id_or_name)
        return render_template("version_detail.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/version_group/<id_or_name>")
def get_version_group(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("version-group", id_or_name)
        return render_template("version_group_detail.html", data=data)
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

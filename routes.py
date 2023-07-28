import logging
import math
import requests
from flask import Blueprint, render_template, request

from pokedex import utils

pokemon_bp = Blueprint(
    "pokemon", __name__, template_folder="templates", static_folder="static"
)

BASE_URL = "https://pokeapi.co/api/v2"
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites"


@pokemon_bp.route("/")
def index():
    return render_template("index.html")


@pokemon_bp.route('/pokemon/')
def get_pokemon_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    endpoint = f"{BASE_URL}/pokemon/?limit={per_page}&offset={offset}"

    response = requests.get(endpoint)
    data = response.json()

    pokemon_list = []

    # Fetch details for each Pokémon in the current set
    for pokemon in data["results"]:
        pokemon = utils.APIResource.fetch_data("pokemon", pokemon["name"])
        pokemon_list.append(pokemon)

    return render_template('list.html', pokemon_list=pokemon_list, current_page=page)


@pokemon_bp.route("/pokemon/<id_or_name>")
def get_pokemon_detail(id_or_name):
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

        data = utils.APIResource.fetch_data(
            "pokemon",
            id_or_name,
            # custom={"location_area_encounters": get_location_area_encounters}, **kwargs
        )
        # some pokemon have encounters /pokemon/<id_or_name>/encounters, need to figure out how to handle

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
        }

        species_data = utils.pokemon_species(data["id"])
        # logging.info(f"species_data: {species_data}")

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

        evolution_id = utils.get_species_id_from_url(species_data['evolution_chain']['url'])
        print(f"Evolution ID: {evolution_id}")
        # Using evolution_id get the chain
        evolution_chain_data = utils.evolution_chain(evolution_id)
        pokemon_name = evolution_chain_data["chain"]["species"]["name"]
        # logging.info(f"name being fed to chain: {pokemon_name}")
        evolution_chain = utils.get_chain(evolution_chain_data, pokemon_name)

        return render_template(
            "detail.html",
            data=data,
            species_data=species_data,
            sorted_sprites=sorted_sprites,
            evolution_chain=evolution_chain,
        )
    else:
        return "Pokemon not found", 404


@pokemon_bp.route("/ability/<id_or_name>")
def get_ability(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = utils.APIResource.fetch_data("ability", id_or_name)
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
        data = utils.APIResource.fetch_data("berry", id_or_name)
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
        data = utils.APIResource.fetch_data("berry-firmness", id_or_name)
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
        data = utils.APIResource.fetch_data("berry-flavor", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/characteristic/<int:id_>")
def get_characteristic(id_):
    try:
        data = utils.APIResource.fetch_data("characteristic", id_)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/contest_effect/<int:id_>")
def get_contest_effect(id_):
    try:
        data = utils.APIResource.fetch_data("contest-effect", id_)
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
        data = utils.APIResource.fetch_data("contest-type", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/super_contest_effect/<int:id_>")
def get_super_contest_effect(id_):
    try:
        data = utils.APIResource.fetch_data("super-contest-effect", id_)
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
        data = utils.APIResource.fetch_data("egg-group", id_or_name)
        return render_template("generic.html", data=data)
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
        data = utils.APIResource.fetch_data("encounter-condition", id_or_name)
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
        data = utils.APIResource.fetch_data("encounter-condition-value", id_or_name)
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
        data = utils.APIResource.fetch_data("encounter-method", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/evolution_chain/<int:id_>")
def get_evolution_chain(id_):
    try:
        data = utils.APIResource.fetch_data("evolution-chain", id_)
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
        data = utils.APIResource.fetch_data("evolution-trigger", id_or_name)
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
        data = utils.APIResource.fetch_data("gender", id_or_name)
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
        data = utils.APIResource.fetch_data("generation", id_or_name)
        return render_template("generic.html", data=data)
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
        data = utils.APIResource.fetch_data("growth-rate", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/item/<id_or_name>")
def get_item(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = utils.APIResource.fetch_data("item", id_or_name)
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
        data = utils.APIResource.fetch_data("item-attribute", id_or_name)
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
        data = utils.APIResource.fetch_data("item-category", id_or_name)
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
        data = utils.APIResource.fetch_data("item-fling-effect", id_or_name)
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
        data = utils.APIResource.fetch_data("item-pocket", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/machine/<int:id_>")
def get_machine(id_):
    try:
        data = utils.APIResource.fetch_data("machine", id_)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move/<id_or_name>")
def get_move(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = utils.APIResource.fetch_data("move", id_or_name)
        return render_template("move.html", data=data)
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
        data = utils.APIResource.fetch_data("move-ailment", id_or_name)
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
        data = utils.APIResource.fetch_data("move-battle-style", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_category/<id_or_name>")
def get_move_category(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = utils.APIResource.fetch_data("move-category", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/move_damage_class/<id_or_name>")
def get_move_damage_class(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = utils.APIResource.fetch_data("move-damage-class", id_or_name)
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
        data = utils.APIResource.fetch_data("move-learn-method", id_or_name)
        return render_template("generic.html", data=data)
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
        data = utils.APIResource.fetch_data("move-target", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/location/<int:id_>")
def get_location(id_):
    try:
        data = utils.APIResource.fetch_data("location", id_)
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
        data = utils.APIResource.fetch_data("location-area", id_or_name)
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
        data = utils.APIResource.fetch_data("pal-park-area", id_or_name)
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
        data = utils.APIResource.fetch_data("pokeathlon-stat", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokedex/<id_or_name>")
def get_pokedex(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = utils.APIResource.fetch_data("pokedex", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon_color/<id_or_name>")
def get_pokemon_color(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = utils.APIResource.fetch_data("pokemon-color", id_or_name)
        return render_template("generic.html", data=data)
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
        data = utils.APIResource.fetch_data("pokemon-form", id_or_name)
        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/pokemon_habitat/<id_or_name>")
def get_pokemon_habitat(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = utils.APIResource.fetch_data("pokemon-habitat", id_or_name)
        return render_template("generic.html", data=data)
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
        data = utils.APIResource.fetch_data("pokemon-shape", id_or_name)
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

        data = utils.APIResource.fetch_data("pokemon-species", id_or_name,
                                             custom={"evolution_chain": get_evolution_chain})
        return data
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
        data = utils.APIResource.fetch_data("region", id_or_name)
        return data
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
        data = utils.APIResource.fetch_data("stat", id_or_name)
        return data
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@pokemon_bp.route("/type/<id_or_name>")
def get_type(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = utils.APIResource.fetch_data("type", id_or_name)
        return data
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
        print(f"id_or_name: {id_or_name}, Type: {type(id_or_name)}")

        # Check if the function exists in the utils module
        if hasattr(utils, endpoint_pythonic):
            func = getattr(utils, endpoint_pythonic)  # get the function from utils by its name
            data = func(id_or_name)
            return render_template("generic.html", data=data)
        else:
            raise ValueError(f"No such endpoint: {api_endpoint}")
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status

# routes/pokemon.py
import logging
import markdown
import requests
from requests.exceptions import HTTPError
from flask import (
    Blueprint,
    render_template,
    abort,
    url_for,
    request,
    json,
    redirect,
    jsonify,
)
from markupsafe import Markup
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.exceptions import HTTPException
from limiter import limiter

import pokedex
from cache import cache
from pokedex.helper import (
    fetch_all_results,
    create_pokemon_list,
    get_summary,
    get_pokemon_cards,
)
from pokedex.utils import Config, resources_dict
from pokedex import APIResource
from pokedex.interface import name_id_convert
from routes.utilities import get_endpoint_data
from .sprite import get_sprite_url
from pokedex.lists import PokemonList

pokemon_bp = Blueprint(
    "pokemon", __name__, template_folder="templates", static_folder="static"
)

BASE_URL = Config.BASE_URL
POKEMON_PER_PAGE = Config.POKEMON_PER_PAGE
ITEMS_PER_PAGE = Config.ITEMS_PER_PAGE
VALID_SPRITES = Config.VALID_SPRITES
TYPE_COLORS = Config.TYPE_COLORS

# Add type data cache at module level
_type_cache = {}


@pokemon_bp.context_processor
def inject_resources():
    return dict(resources_json=json.dumps(resources_dict))


@pokemon_bp.route("/resources.js")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def serve_resources_js():
    """Serve resources data as a JavaScript file for CSP compliance."""
    from flask import make_response
    # Use the same method as the context processor
    context_data = inject_resources()
    resources_json = context_data['resources_json']
    js_content = f"const resources = {resources_json};"
    response = make_response(js_content)
    response.headers['Content-Type'] = 'application/javascript'
    return response


def fetch_count(endpoint):
    """Fetch count for a specific endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}?limit=1")
        if response.status_code == 200:
            return endpoint, response.json()["count"]
        logging.error(f"Error fetching {endpoint} count: Status {response.status_code}")
        return endpoint, 0
    except Exception as e:
        logging.error(f"Error fetching count for {endpoint}: {e}")
        return endpoint, 0


@pokemon_bp.route("/")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def index():
    endpoints = {
        "pokemon": "pokemon_count",
        "type": "types_count",
        "ability": "abilities_count",
        "pokemon-color": "color_count",
        "pokemon-habitat": "habitat_count",
        "pokemon-shape": "shape_count",
    }

    counts = {}
    try:
        with ThreadPoolExecutor(max_workers=6) as executor:
            # Submit all requests concurrently
            future_to_endpoint = {
                executor.submit(fetch_count, endpoint): endpoint
                for endpoint in endpoints.keys()
            }

            # Collect results as they complete
            for future in as_completed(future_to_endpoint):
                endpoint, count = future.result()
                counts[endpoints[endpoint]] = count

        return render_template("index.html", **counts)
    except Exception as e:
        logging.error(f"Error fetching counts: {e}")
        # Fallback to zero counts if there's an error
        return render_template(
            "index.html",
            pokemon_count=0,
            types_count=0,
            abilities_count=0,
            color_count=0,
            habitat_count=0,
            shape_count=0,
        )


@pokemon_bp.route("/detective-pikachu")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_detective_pikachu_pokemon():
    # List of Pokémon featured in the Detective Pikachu movie
    detective_pikachu_pokemon = [
        "pikachu",
        "psyduck",
        "mewtwo",
        "charmander",
        "charizard",
        "greninja",
        "mr-mime",
        "bulbasaur",
        "jigglypuff",
        "ditto",
        "eevee",
        "flareon",
        "snubbull",
        "torterra",
        "aipom",
        "cubone",
        "pancham",
        "pangoro",
        "gengar",
        "machamp",
        "lickitung",
        "growlithe",
        "slaking",
        "morelull",
        "rufflet",
        "pidgeot",
        "pidgey",
        "emolga",
        "dodrio",
        "magikarp",
        "gyarados",
        "treecko",
        "rattata",
        "kingler",
        "squirtle",
        "ludicolo",
        "loudred",
        "comfey",
        "blastoise",
        "arcanine",
        "sneasel",
        "venusaur",
        "purrloin",
        "braviary",
    ]

    # Transform the list into the expected format for create_pokemon_list
    pokemon_list = [{"name": name} for name in detective_pikachu_pokemon]

    # Create the Pokémon list with sprites
    pokemon_list = create_pokemon_list(pokemon_list)

    # Render a template for the Detective Pikachu Pokémon
    return render_template("detective_pikachu.html", pokemon_list=pokemon_list)


@pokemon_bp.route("/pokedex/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokedex/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_pokedex(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/pokedex"
        data = fetch_all_results(url)
        return render_template("pokedex.html", data=data)
    else:
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass

        try:
            data = pokedex.APIResource.fetch_data("pokedex", id_or_name)
        except ValueError as e:
            logging.error(f"ValueError in fetching pokedex {id_or_name}: {e}")
            abort(404, description=f"Pokedex '{id_or_name}' not found")
        except HTTPError as e:
            if e.response.status_code == 404:
                abort(404, description=f"Pokedex '{id_or_name}' not found")
            else:
                logging.error(f"HTTP error occurred: {e}")
                abort(500, description=str(e))
        except Exception as e:
            logging.exception(
                f"Unexpected error occurred while fetching Pokedex {id_or_name}: {e}"
            )
            abort(500, description="An unexpected error occurred")

        if not data or "name" not in data:
            logging.warning(f"No data found for Pokedex: {id_or_name}")
            abort(404, description=f"Pokedex '{id_or_name}' not found")

        # Process pokemon_entries from the Pokedex
        pokemon_list = []
        if "pokemon_entries" in data and data["pokemon_entries"]:
            entries_count = len(data["pokemon_entries"])

            # Create a list for parallel processing
            pokemon_requests = []

            for entry in data["pokemon_entries"]:
                if "pokemon_species" in entry and "name" in entry["pokemon_species"]:
                    species_name = entry["pokemon_species"]["name"]
                    entry_number = entry.get("entry_number")
                    pokemon_requests.append(
                        {"name": species_name, "entry_number": entry_number}
                    )

            # Process entries in batches to prevent overwhelming the API
            batch_size = 50
            total_entries = len(pokemon_requests)
            processed = 0

            for i in range(0, total_entries, batch_size):
                batch = pokemon_requests[i : i + batch_size]
                batch_pokemon_list = create_pokemon_list(batch)

                # Add entry_number to each Pokémon in the list
                for j, pokemon in enumerate(batch_pokemon_list):
                    if i + j < total_entries:
                        pokemon["entry_number"] = pokemon_requests[i + j][
                            "entry_number"
                        ]

                pokemon_list.extend(batch_pokemon_list)
                processed += len(batch)

            # Sort the list by entry number
            pokemon_list.sort(key=lambda x: x.get("entry_number", float("inf")))

        return render_template(
            "pokedex_detail.html", data=data, pokemon_list=pokemon_list
        )


@pokemon_bp.route("/pokemon/")
def get_pokemon_list():
    page = request.args.get("page", 1, type=int)
    per_page = POKEMON_PER_PAGE
    offset = (page - 1) * per_page
    endpoint = f"{BASE_URL}/pokemon/?limit={per_page}&offset={offset}"

    response = requests.get(endpoint)
    data = response.json()

    # Create pokemon list using the helper function
    pokemon_list = create_pokemon_list(data["results"])

    return render_template(
        "pokemon_list.html", pokemon_list=pokemon_list, current_page=page
    )


@pokemon_bp.route("/pokemon/<id_or_name>")
def get_pokemon(id_or_name):

    try:
        try:
            id_or_name = int(id_or_name)
            logging.info(f"Converted id_or_name to integer: {id_or_name}")
        except ValueError:
            logging.info(f"Using id_or_name as string: {id_or_name}")
            pass

        logging.info(f"Attempting to fetch pokemon data for: {id_or_name}")
        data = pokedex.APIResource.fetch_data("pokemon", id_or_name)
    except ValueError as e:
        logging.error(f"ValueError in get_pokemon for {id_or_name}: {str(e)}")
        # Try pokemon-species endpoint
        try:
            logging.info(f"Attempting to fetch pokemon-species data for: {id_or_name}")
            return redirect(
                url_for("pokemon.get_pokemon_species", id_or_name=id_or_name)
            )
        except Exception as e:
            logging.error(f"Error fetching pokemon-species data: {e}")
            abort(404, description=f"Pokemon '{id_or_name}' not found")
    except HTTPError as e:
        logging.error(f"HTTPError in get_pokemon for {id_or_name}: {str(e)}")
        if e.response.status_code == 404:
            # Try pokemon-species endpoint
            try:
                logging.info(
                    f"Attempting to fetch pokemon-species data for: {id_or_name}"
                )
                return redirect(
                    url_for("pokemon.get_pokemon_species", id_or_name=id_or_name)
                )
            except Exception as e:
                logging.error(f"Error fetching pokemon-species data: {e}")
                abort(404, description=f"Pokemon '{id_or_name}' not found")
        else:
            logging.error(f"HTTP error occurred: {e}")
            abort(500, description=str(e))
    except Exception as e:
        logging.error(f"Error in get_pokemon for {id_or_name}: {str(e)}")
        abort(500, description=str(e))

    if not data or "name" not in data:
        logging.warning(f"Pokemon data missing or invalid for: {id_or_name}")
        # Try pokemon-species endpoint
        try:
            logging.info(f"Attempting to fetch pokemon-species data for: {id_or_name}")
            return redirect(
                url_for("pokemon.get_pokemon_species", id_or_name=id_or_name)
            )
        except Exception as e:
            logging.error(f"Error fetching pokemon-species data: {e}")
            abort(404, description=f"Pokemon '{id_or_name}' not found")

    # Initialize variables
    species_data = None
    evolution_chain = None
    type_effectiveness = None
    move_categories = {
        "level_up": [],
        "tm_hm": [],
        "breeding": [],
        "tutor": [],
        "other": [],
    }

    # Categorize moves by how they're learned using a dictionary mapping
    move_method_mapping = {
        "level-up": "level_up",
        "machine": "tm_hm",
        "egg": "breeding",
        "tutor": "tutor",
    }

    # Process all moves at once
    for move_detail in data.get("moves", []):
        version_details = move_detail["version_group_details"][
            0
        ]  # Get the first version group details
        move_learned_method = version_details["move_learn_method"]["name"]

        move_data = {
            "name": move_detail["move"]["name"].replace("-", " ").title(),
            "url": url_for(
                "abilities_moves_items.get_move",
                id_or_name=move_detail["move"]["name"],
            ),
            "level_learned_at": version_details["level_learned_at"],
        }

        # Use the mapping to categorize moves, defaulting to "other"
        category = move_method_mapping.get(move_learned_method, "other")
        move_categories[category].append(move_data)

    # Sort level-up moves by level
    move_categories["level_up"].sort(key=lambda x: x["level_learned_at"])

    try:
        species_data = pokedex.APIResource.fetch_data(
            "pokemon-species", data["species"]["name"]
        )
        if species_data:
            # Get evolution chain if available
            if "evolution_chain" in species_data and species_data[
                "evolution_chain"
            ].get("url"):
                evolution_id = pokedex.get_species_id_from_url(
                    species_data["evolution_chain"]["url"]
                )
                evolution_chain_data = pokedex.APIResource.fetch_data(
                    "evolution-chain", evolution_id
                )
                if evolution_chain_data:
                    pokemon_name = evolution_chain_data["chain"]["species"]["name"]
                    evolution_chain = pokedex.get_chain(
                        evolution_chain_data, pokemon_name
                    )

            # Get entry number from first pokedex number
            entry_number = next(
                (
                    entry.get("entry_number")
                    for entry in species_data.get("pokedex_numbers", [])
                    if "entry_number" in entry
                ),
                None,
            )
    except requests.exceptions.HTTPError as e:
        logging.warning(f"HTTP error fetching species data for {data['name']}: {e}")
    except Exception as e:
        logging.error(f"Error processing species data for {data['name']}: {e}")

    # Get official artwork (use species id for forms so upstream asset exists)
    official_artwork = None
    try:
        if data["id"]:
            species = data.get("species") or {}
            species_url = species.get("url") if isinstance(species, dict) else None
            artwork_id = (
                pokedex.get_species_id_from_url(species_url)
                if species_url
                else data["id"]
            )
            official_artwork = get_sprite_url(artwork_id, is_artwork=True)
    except Exception as e:
        logging.warning(f"Error getting official artwork for {data['name']}: {e}")

    # Get the sprite data and filter out null values and unwanted sprites
    valid_sprite_keys = {
        key: value
        for key, value in data["sprites"].items()
        if value is not None and key in VALID_SPRITES
    }

    # Generate URLs only for sprites that exist
    sprites = {}
    try:
        if (
            data["id"] and valid_sprite_keys
        ):  # If we have a valid Pokemon ID and sprites
            sprites = {
                sprite_type: get_sprite_url(data["id"], sprite_type=sprite_type)
                for sprite_type in valid_sprite_keys.keys()
            }
    except Exception as e:
        logging.warning(f"Error generating sprite URLs for {data['name']}: {e}")

    # Sort sprites according to VALID_SPRITES order
    sorted_sprites = {key: sprites[key] for key in VALID_SPRITES if key in sprites}

    # Retrieve the summary for the Pokémon
    summary = get_summary(data["name"], "pokemon")

    # Convert the markdown summary to HTML, ensuring summary is a string
    summary_html = (
        Markup(markdown.markdown(str(summary)))
        if summary and isinstance(summary, str)
        else None
    )

    try:
        cards = get_pokemon_cards(data["name"])
    except Exception as e:
        # Log the exception and proceed with an empty list
        logging.debug(f"Error fetching cards for {data['name']}: {e}")
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
        official_artwork=official_artwork,
    )


@pokemon_bp.route("/pokemon-color/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon-color/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_pokemon_color(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/pokemon-color"
        colors = fetch_all_results(url)
        return render_template("colors.html", colors=colors)
    else:
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass

        try:
            data = pokedex.APIResource.fetch_data("pokemon-color", id_or_name)
        except ValueError as e:
            logging.error(f"ValueError in fetching color {id_or_name}: {e}")
            abort(404, description=f"Pokemon color '{id_or_name}' not found")
        except HTTPError as e:
            if e.response.status_code == 404:
                abort(404, description=f"Pokemon color '{id_or_name}' not found")
            else:
                logging.error(f"HTTP error occurred: {e}")
                abort(500, description=str(e))
        except Exception as e:
            logging.exception(
                f"Unexpected error occurred while fetching Pokemon color {id_or_name}: {e}"
            )
            abort(500, description="An unexpected error occurred")

        if not data or "name" not in data:
            logging.warning(f"No data found for Pokemon color: {id_or_name}")
            abort(404, description=f"Pokemon color '{id_or_name}' not found")

        pokemon_list = pokedex.PokemonList(data).create_pokemon_list()
        return render_template(
            "color_detail.html", data=data, pokemon_list=pokemon_list
        )


@pokemon_bp.route("/pokemon-form/<id_or_name>")
def get_pokemon_form(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    try:
        data = pokedex.APIResource.fetch_data("pokemon-form", id_or_name)
    except ValueError as e:
        logging.error(f"ValueError in fetching form {id_or_name}: {e}")
        abort(404, description=f"Pokemon form '{id_or_name}' not found")
    except HTTPError as e:
        if e.response.status_code == 404:
            abort(404, description=f"Pokemon form '{id_or_name}' not found")
        else:
            logging.error(f"HTTP error occurred: {e}")
            abort(500, description=str(e))
    except Exception as e:
        logging.exception(
            f"Unexpected error occurred while fetching Pokemon form {id_or_name}: {e}"
        )
        abort(500, description="An unexpected error occurred")

    if not data or "name" not in data:
        logging.warning(f"No data found for Pokemon form: {id_or_name}")
        abort(404, description=f"Pokemon form '{id_or_name}' not found")

    return render_template("generic.html", data=data)


@pokemon_bp.route("/pokemon-habitat/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon-habitat/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_pokemon_habitat(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/pokemon-habitat"
        habitats = fetch_all_results(url)
        return render_template("habitats.html", habitats=habitats)
    else:
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass

        try:
            data = pokedex.APIResource.fetch_data("pokemon-habitat", id_or_name)
        except ValueError as e:
            logging.error(f"ValueError in fetching habitat {id_or_name}: {e}")
            abort(404, description=f"Pokemon habitat '{id_or_name}' not found")
        except HTTPError as e:
            if e.response.status_code == 404:
                abort(404, description=f"Pokemon habitat '{id_or_name}' not found")
            else:
                logging.error(f"HTTP error occurred: {e}")
                abort(500, description=str(e))
        except Exception as e:
            logging.exception(
                f"Unexpected error occurred while fetching Pokemon habitat {id_or_name}: {e}"
            )
            abort(500, description="An unexpected error occurred")

        if not data or "name" not in data:
            logging.warning(f"No data found for Pokemon habitat: {id_or_name}")
            abort(404, description=f"Pokemon habitat '{id_or_name}' not found")

        pokemon_list = create_pokemon_list(data)
        return render_template(
            "habitat_detail.html", data=data, pokemon_list=pokemon_list
        )


@pokemon_bp.route("/pokemon-shape/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon-shape/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_pokemon_shape(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/pokemon-shape"
        types = fetch_all_results(url)
        return render_template("shapes.html", types=types)
    else:
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass

        try:
            data = pokedex.APIResource.fetch_data("pokemon-shape", id_or_name)
        except ValueError as e:
            logging.error(f"ValueError in fetching shape {id_or_name}: {e}")
            abort(404, description=f"Pokemon shape '{id_or_name}' not found")
        except HTTPError as e:
            if e.response.status_code == 404:
                abort(404, description=f"Pokemon shape '{id_or_name}' not found")
            else:
                logging.error(f"HTTP error occurred: {e}")
                abort(500, description=str(e))
        except Exception as e:
            logging.exception(
                f"Unexpected error occurred while fetching Pokemon shape {id_or_name}: {e}"
            )
            abort(500, description="An unexpected error occurred")

        if not data or "name" not in data:
            logging.warning(f"No data found for Pokemon shape: {id_or_name}")
            abort(404, description=f"Pokemon shape '{id_or_name}' not found")

        pokemon_list = create_pokemon_list(data)
        return render_template(
            "shape_detail.html", data=data, pokemon_list=pokemon_list
        )


@pokemon_bp.route("/pokemon-species/", defaults={"id_or_name": None})
@pokemon_bp.route("/pokemon-species/<id_or_name>")
def get_pokemon_species(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/pokemon-species"
        data = fetch_all_results(url)
        return render_template("pokemon_species.html", data=data)
    else:
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass

        try:
            data = pokedex.APIResource.fetch_data("pokemon-species", id_or_name)
        except ValueError as e:
            logging.error(f"ValueError in fetching species {id_or_name}: {e}")
            abort(404, description=f"Pokemon species '{id_or_name}' not found")
        except HTTPError as e:
            if e.response.status_code == 404:
                abort(404, description=f"Pokemon species '{id_or_name}' not found")
            else:
                logging.error(f"HTTP error occurred: {e}")
                abort(500, description=str(e))
        except Exception as e:
            logging.exception(
                f"Unexpected error occurred while fetching Pokemon species {id_or_name}: {e}"
            )
            abort(500, description="An unexpected error occurred")

        if not data or "name" not in data:
            logging.warning(f"No data found for Pokemon species: {id_or_name}")
            abort(404, description=f"Pokemon species '{id_or_name}' not found")

        try:
            simplified_data = {"pokemon_species": [{"name": data.get("name")}]}
            pokemon_list = pokedex.PokemonList(simplified_data).create_pokemon_list()
            return render_template(
                "pokemon_species_detail.html", data=data, pokemon_list=pokemon_list
            )
        except Exception as e:
            logging.exception(f"Error processing species data for {id_or_name}: {e}")
            abort(
                500, description="An error occurred while processing the species data"
            )

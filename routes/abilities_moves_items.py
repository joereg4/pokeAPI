# routes/abilities_items.py
import logging
import markdown
import pandas as pd
import re
import requests
from flask import Blueprint, render_template, abort, request
from markupsafe import Markup
from requests.exceptions import HTTPError

import pokedex
from cache import cache
from pokedex.helper import (
    fetch_all_results,
    get_summary,
    get_path,
    create_pokemon_list,
    get_pokemon_cards,
)
from pokedex.utils import Config

abilities_moves_items_bp = Blueprint(
    "abilities_moves_items",
    __name__,
    template_folder="templates",
    static_folder="static",
)

BASE_URL = Config.BASE_URL
ITEMS_PER_PAGE = Config.ITEMS_PER_PAGE


@abilities_moves_items_bp.route("/ability/", defaults={"id_or_name": None})
@abilities_moves_items_bp.route("/ability/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_ability(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the abilities list
        url = f"{BASE_URL}/ability"
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
            pokemon_list = create_pokemon_list(data.get("pokemon", []))

            # Fetch Summary
            summary = get_summary(data["name"], "ability")

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template(
                "ability_detail.html",
                data=data,
                pokemon_list=pokemon_list,
                summary_html=summary_html,
            )
        except ValueError as e:
            abort(404, description=str(e))


@abilities_moves_items_bp.route("/item/", defaults={"id_or_name": None})
@abilities_moves_items_bp.route("/item/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_item(id_or_name):
    if id_or_name is None:
        # Fetch all items
        url = f"{BASE_URL}/item"
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
            pokemon_list = create_pokemon_list(data.get("held_by_pokemon", []))

            # Fetch Summary
            summary = get_summary(data["name"], "item")

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            try:
                name = '"{}"'.format(data["name"])
                # Replace '-' with ' ' before calling get_pokemon_cards
                # cards = get_pokemon_cards(name.replace("-", " "))
                cards = []  # Temporarily disable Pokemon card fetching
            except Exception as e:
                # Log the exception and proceed with an empty list
                logging.debug(
                    f"Error fetching cards for {data['name'].replace('-', '+')}: {e}"
                )
                cards = []

            return render_template(
                "item_detail.html",
                data=data,
                pokemon_list=pokemon_list,
                summary_html=summary_html,
                cards=cards,
            )
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@abilities_moves_items_bp.route("/item-attribute/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
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
        return render_template(
            "item_attribute_detail.html", data=data, items_list=items_list
        )
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@abilities_moves_items_bp.route("/item-category/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
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

        return render_template("item_category_detail.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@abilities_moves_items_bp.route("/machine/<int:id_>")
def get_machine(id_):
    try:
        # Fetch machine data
        machine_data = pokedex.APIResource.fetch_data("machine", id_)

        # Fetch related data: item, move, and version group
        item_data = pokedex.APIResource.fetch_data("item", machine_data["item"]["name"])
        move_data = pokedex.APIResource.fetch_data("move", machine_data["move"]["name"])
        version_group_data = pokedex.APIResource.fetch_data(
            "version-group", machine_data["version_group"]["name"]
        )

        # Handle cases where any of the data is missing or invalid
        if not all([item_data, move_data, version_group_data]):
            abort(404, description=f"Machine '{id_}' not found or incomplete data.")

        return render_template(
            "machine_detail.html",
            machine_data=machine_data,
            item_data=item_data,
            move_data=move_data,
            version_group_data=version_group_data,
        )
    except (ValueError, HTTPError) as e:
        # Handle HTTP errors or other exceptions
        if isinstance(e, HTTPError) and e.response.status_code == 404:
            abort(404, description=f"Machine '{id_}' not found")
        else:
            logging.debug(f"Error occurred: {e}")
            return str(e), 500  # Internal Server Error for other issues


@abilities_moves_items_bp.route("/machine/page/<int:page>")
@abilities_moves_items_bp.route("/machine/", defaults={"page": 1})
def get_machines(page=1):
    try:
        per_page = ITEMS_PER_PAGE  # Number of machines to display per page
        offset = (page - 1) * per_page
        url = f"{BASE_URL}/machine?offset={offset}&limit={per_page}"

        response = requests.get(url)
        if response.status_code != 200:
            abort(500, description="Failed to fetch machine data from the API")

        data = response.json()

        complete_machines = []

        # Process the results and extract the ID for each machine
        for machine in data["results"]:
            machine_id = int(re.search(r"/(\d+)/$", machine["url"]).group(1))
            machine_data = pokedex.APIResource.fetch_data("machine", machine_id)

            # Fetch related data: item, move, and version group
            item_data = pokedex.APIResource.fetch_data(
                "item", machine_data["item"]["name"]
            )
            move_data = pokedex.APIResource.fetch_data(
                "move", machine_data["move"]["name"]
            )
            version_group_data = pokedex.APIResource.fetch_data(
                "version-group", machine_data["version_group"]["name"]
            )

            # Combine details into a single dictionary
            machine_detail = {
                "id": machine_id,
                "item": item_data,
                "move": move_data,
                "version_group": version_group_data,
            }

            complete_machines.append(machine_detail)

        total_count = data["count"]
        total_pages = (total_count + per_page - 1) // per_page

        return render_template(
            "machine.html", data=complete_machines, page=page, total_pages=total_pages
        )
    except (ValueError, HTTPError) as e:
        # Handle HTTP errors or other exceptions
        if isinstance(e, HTTPError) and e.response.status_code == 404:
            abort(404, description=f"Machine endpoint failed")
        else:
            logging.debug(f"Error occurred: {e}")
            return str(e), 500  # Internal Server Error for other issues


@abilities_moves_items_bp.route("/move/")
def get_moves_list():
    page = request.args.get("page", 1, type=int)
    per_page = ITEMS_PER_PAGE
    offset = (page - 1) * per_page
    endpoint = f"{BASE_URL}/move/?limit={per_page}&offset={offset}"

    response = requests.get(endpoint)
    if response.status_code != 200:
        logging.error(f"Error fetching moves: {response.status_code} - {response.text}")
        abort(500, description="Failed to fetch moves from the API.")

    moves_list = response.json()
    return render_template("moves.html", moves_list=moves_list, current_page=page)


@abilities_moves_items_bp.route("/move/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_move(id_or_name):
    if id_or_name is None:
        # Fetch all moves
        url = f"{BASE_URL}/move"
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

            pokemon_list = create_pokemon_list(data.get("learned_by_pokemon", []))

            # Check if the category data exists and is not None
            category = None
            if data.get("meta") and data["meta"].get("category"):
                category_name = data["meta"]["category"]["name"]
                category = pokedex.APIResource.fetch_data(
                    "move-category", category_name
                )
            else:
                logging.debug(f"No category found for move {data['name']}")

            # Fetch Summary
            summary = get_summary(data["name"], "move")

            # Convert the markdown summary to HTML
            summary_html = Markup(markdown.markdown(summary)) if summary else None

            return render_template(
                "move_detail.html",
                data=data,
                category=category,
                pokemon_list=pokemon_list,
                summary_html=summary_html,
            )
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@abilities_moves_items_bp.route("/move-category/", defaults={"id_or_name": None})
@abilities_moves_items_bp.route("/move-category/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_move_category(id_or_name):
    try:
        if id_or_name is None:
            # Fetch all move categories
            url = f"{BASE_URL}/move-category"
            data = fetch_all_results(url)
            return render_template("move_categories.html", data=data)
        else:
            try:
                # Fetch details for a specific move
                id_or_name = int(id_or_name)
            except ValueError:
                pass  # If the conversion fails, it remains a string

            # Fetch details for a specific move category
            category = pokedex.APIResource.fetch_data("move-category", id_or_name)
            if "name" not in category:
                abort(404, description=f"Move Category '{id_or_name}' not found")

            moves = []
            for move in category["moves"]:
                try:
                    move_detail = pokedex.APIResource.fetch_data("move", move["name"])
                    moves.append(move_detail)
                except Exception as e:
                    logging.error(f"Error fetching move {move['name']}: {str(e)}")
                    continue

            return render_template(
                "move_category_detail.html",
                category=category,
                moves=moves,
            )
    except Exception as e:
        return str(e), 404


@abilities_moves_items_bp.route("/move-damage-class/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_move_damage_class(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        damage_class = pokedex.APIResource.fetch_data("move-damage-class", id_or_name)

        if "name" not in damage_class:
            abort(404, description=f"Move Damage Class '{id_or_name}' not found")

        return render_template(
            "move_damage_class_detail.html", damage_class=damage_class
        )
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@abilities_moves_items_bp.route("/move-learn-method/", defaults={"id_or_name": None})
@abilities_moves_items_bp.route("/move-learn-method/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_move_learn_method(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the move learn method list
        url = f"{BASE_URL}/move-learn-method"
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



# routes/abilities_moves_items.py
import logging
import markdown
import pandas as pd
import re
from flask import Blueprint, render_template, abort, request
from markupsafe import Markup

import pokedex
from cache import cache
from pokedex.client import client as pokeapi
from pokedex.helper import (
    fetch_all_results,
    get_summary,
    get_path,
    get_pokemon_cards,
)
from pokedex.services import build_pokemon_list
from pokedex.utils import Config
from pokedex.serializers import serialize_ability, serialize_move, serialize_item
from routes.decorators import handle_api_errors

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
@handle_api_errors("Ability")
def get_ability(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/ability"
        abilities = fetch_all_results(url)
        return render_template("abilities.html", abilities=abilities)

    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("ability", id_or_name)

    if "name" not in data:
        abort(404, description=f"Ability '{id_or_name}' not found")

    pokemon_list = build_pokemon_list(data.get("pokemon", []))
    summary = get_summary(data["name"], "ability")
    summary_html = Markup(markdown.markdown(summary)) if summary else None

    return render_template(
        "ability_detail.html",
        data=serialize_ability(data),
        pokemon_list=pokemon_list,
        summary_html=summary_html,
    )


@abilities_moves_items_bp.route("/item/", defaults={"id_or_name": None})
@abilities_moves_items_bp.route("/item/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Item")
def get_item(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/item"
        data = fetch_all_results(url)
        return render_template("items.html", data=data)

    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("item", id_or_name)

    if "name" not in data:
        abort(404, description=f"Item '{id_or_name}' not found")

    pokemon_list = build_pokemon_list(data.get("held_by_pokemon", []))
    summary = get_summary(data["name"], "item")
    summary_html = Markup(markdown.markdown(summary)) if summary else None

    try:
        name = '"{}"'.format(data["name"])
        cards = []  # Temporarily disable Pokemon card fetching
    except Exception as e:
        logging.debug(
            f"Error fetching cards for {data['name'].replace('-', '+')}: {e}"
        )
        cards = []

    return render_template(
        "item_detail.html",
        data=serialize_item(data),
        pokemon_list=pokemon_list,
        summary_html=summary_html,
        cards=cards,
    )


@abilities_moves_items_bp.route("/item-attribute/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Item Attribute")
def get_item_attribute(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("item-attribute", id_or_name)

    if "name" not in data:
        abort(404, description=f"Item Attribute '{id_or_name}' not found")

    items_list = data.pop("items", [])
    return render_template(
        "item_attribute_detail.html", data=data, items_list=items_list
    )


@abilities_moves_items_bp.route("/item-category/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Item Category")
def get_item_category(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("item-category", id_or_name)

    if "name" not in data:
        abort(404, description=f"Item Category '{id_or_name}' not found")

    return render_template("item_category_detail.html", data=data)


@abilities_moves_items_bp.route("/machine/<int:id_>")
@handle_api_errors("Machine")
def get_machine(id_):
    machine_data = pokedex.APIResource.fetch_data("machine", id_)

    item_data = pokedex.APIResource.fetch_data("item", machine_data["item"]["name"])
    move_data = pokedex.APIResource.fetch_data("move", machine_data["move"]["name"])
    version_group_data = pokedex.APIResource.fetch_data(
        "version-group", machine_data["version_group"]["name"]
    )

    if not all([item_data, move_data, version_group_data]):
        abort(404, description=f"Machine '{id_}' not found or incomplete data.")

    return render_template(
        "machine_detail.html",
        machine_data=machine_data,
        item_data=item_data,
        move_data=move_data,
        version_group_data=version_group_data,
    )


@abilities_moves_items_bp.route("/machine/page/<int:page>")
@abilities_moves_items_bp.route("/machine/", defaults={"page": 1})
@handle_api_errors("Machine")
def get_machines(page=1):
    per_page = ITEMS_PER_PAGE
    offset = (page - 1) * per_page
    data = pokeapi.fetch_list("machine", limit=per_page, offset=offset)

    complete_machines = []

    for machine in data["results"]:
        machine_id = int(re.search(r"/(\d+)/$", machine["url"]).group(1))
        machine_data = pokedex.APIResource.fetch_data("machine", machine_id)

        item_data = pokedex.APIResource.fetch_data(
            "item", machine_data["item"]["name"]
        )
        move_data = pokedex.APIResource.fetch_data(
            "move", machine_data["move"]["name"]
        )
        version_group_data = pokedex.APIResource.fetch_data(
            "version-group", machine_data["version_group"]["name"]
        )

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


@abilities_moves_items_bp.route("/move/")
def get_moves_list():
    page = request.args.get("page", 1, type=int)
    per_page = ITEMS_PER_PAGE
    offset = (page - 1) * per_page
    moves_list = pokeapi.fetch_list("move", limit=per_page, offset=offset)
    return render_template("moves.html", moves_list=moves_list, current_page=page)


@abilities_moves_items_bp.route("/move/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Move")
def get_move(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("move", id_or_name)

    if "name" not in data:
        abort(404, description=f"Pokemon Move '{id_or_name}' not found")

    pokemon_list = build_pokemon_list(data.get("learned_by_pokemon", []))

    # Check if the category data exists and is not None
    category = None
    if data.get("meta") and data["meta"].get("category"):
        category_name = data["meta"]["category"]["name"]
        category = pokedex.APIResource.fetch_data(
            "move-category", category_name
        )
    else:
        logging.debug(f"No category found for move {data['name']}")

    summary = get_summary(data["name"], "move")
    summary_html = Markup(markdown.markdown(summary)) if summary else None

    return render_template(
        "move_detail.html",
        data=serialize_move(data),
        category=category,
        pokemon_list=pokemon_list,
        summary_html=summary_html,
    )


@abilities_moves_items_bp.route("/move-category/", defaults={"id_or_name": None})
@abilities_moves_items_bp.route("/move-category/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Move Category")
def get_move_category(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/move-category"
        data = fetch_all_results(url)
        return render_template("move_categories.html", data=data)

    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

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


@abilities_moves_items_bp.route("/move-damage-class/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Move Damage Class")
def get_move_damage_class(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    damage_class = pokedex.APIResource.fetch_data("move-damage-class", id_or_name)

    if "name" not in damage_class:
        abort(404, description=f"Move Damage Class '{id_or_name}' not found")

    return render_template(
        "move_damage_class_detail.html", damage_class=damage_class
    )


@abilities_moves_items_bp.route("/move-learn-method/", defaults={"id_or_name": None})
@abilities_moves_items_bp.route("/move-learn-method/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Move Learn Method")
def get_move_learn_method(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/move-learn-method"
        data = fetch_all_results(url)
        return render_template("move_learn_methods.html", data=data)

    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("move-learn-method", id_or_name)

    if "name" not in data:
        abort(404, description=f"Move Learn Method '{id_or_name}' not found")

    return render_template("move_learn_method_detail.html", data=data)

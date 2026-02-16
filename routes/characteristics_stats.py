# routes/characteristics_stats.py
import markdown
import pandas as pd
from flask import Blueprint, render_template, abort
from markupsafe import Markup

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results, get_path, get_summary
from pokedex.services import build_pokemon_list
from pokedex.utils import Config
from routes.decorators import handle_api_errors

BASE_URL = Config.BASE_URL
TYPE_COLORS = Config.TYPE_COLORS

characteristics_stats_bp = Blueprint(
    "characteristics_stats",
    __name__,
    template_folder="templates",
    static_folder="static",
)


@characteristics_stats_bp.route("/characteristic/", defaults={"id_": None})
@characteristics_stats_bp.route("/characteristic/<int:id_>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Characteristic")
def get_characteristic(id_):
    if id_ is None:
        url = f"{BASE_URL}/characteristic"
        data = fetch_all_results(url)

        for characteristic in data:
            characteristic["id"] = int(characteristic["url"].split("/")[-2])

        return render_template("characteristics.html", data=data)

    data = pokedex.APIResource.fetch_data("characteristic", id_)

    if "id" not in data:
        abort(404, description=f"Characteristic '{id_}' not found")

    return render_template("characteristic_detail.html", data=data)


@characteristics_stats_bp.route("/stat/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Stat")
def get_stat(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("stat", id_or_name)

    if "name" not in data:
        abort(404, description=f"Stat '{id_or_name}' not found")

    return render_template("stat_detail.html", data=data)


@characteristics_stats_bp.route("/type/", defaults={"id_or_name": None})
@characteristics_stats_bp.route("/type/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Pokemon Type")
def get_type(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/type"
        types = fetch_all_results(url)
        return render_template("types.html", types=types)

    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("type", id_or_name)

    if "name" not in data:
        abort(404, description=f"Pokemon type '{id_or_name}' not found")

    pokemon_list = build_pokemon_list(data.get("pokemon", []))
    summary = get_summary(data["name"], "type")
    summary_html = Markup(markdown.markdown(str(summary))) if summary else None

    return render_template(
        "type_detail.html",
        type_effectiveness=data,
        pokemon_list=pokemon_list,
        type_colors=TYPE_COLORS,
        summary_html=summary_html,
    )

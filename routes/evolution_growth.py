# routes/evolution_growth.py
from flask import Blueprint, render_template, abort

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results
from pokedex.services import build_pokemon_list
from pokedex.utils import Config
from routes.decorators import handle_api_errors

BASE_URL = Config.BASE_URL

evolution_growth_bp = Blueprint(
    "evolution_growth", __name__, template_folder="templates", static_folder="static"
)


@evolution_growth_bp.route("/generation/", defaults={"id_or_name": None})
@evolution_growth_bp.route("/generation/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Generation")
def get_generation(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/generation"
        data = fetch_all_results(url)
        return render_template("generations.html", data=data)

    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("generation", id_or_name)

    if "name" not in data:
        abort(404, description=f"Generation '{id_or_name}' not found")

    pokemon_list = build_pokemon_list(data.get("pokemon_species", []))

    return render_template(
        "generation_detail.html", data=data, pokemon_list=pokemon_list
    )



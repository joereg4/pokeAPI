# routes/evolution_growth.py
import logging
from flask import Blueprint, render_template, abort

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results
from pokedex.services import build_pokemon_list
from pokedex.utils import Config

BASE_URL = Config.BASE_URL

evolution_growth_bp = Blueprint(
    "evolution_growth", __name__, template_folder="templates", static_folder="static"
)


@evolution_growth_bp.route("/generation/", defaults={"id_or_name": None})
@evolution_growth_bp.route("/generation/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_generation(id_or_name):
    if id_or_name is None:
        # Fetch all generations
        url = f"{BASE_URL}/generation"
        data = fetch_all_results(url)
        return render_template("generations.html", data=data)
    else:
        try:
            # Check if id_or_name can be converted to an integer
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("generation", id_or_name)

            if "name" not in data:
                abort(404, description=f"Generation '{id_or_name}' not found")

            pokemon_list = build_pokemon_list(data.get("pokemon_species", []))

            return render_template(
                "generation_detail.html", data=data, pokemon_list=pokemon_list
            )
        except ValueError as e:
            msg = str(e)
            if "not found" in msg.lower():
                abort(404, description=msg)
            abort(400, description=msg)



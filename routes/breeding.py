# routes/breeding.py
import logging
import markdown
import pandas as pd
from markupsafe import Markup
from flask import Blueprint, render_template, abort

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results, get_summary, get_path
from pokedex.services import build_pokemon_list
from pokedex.utils import Config

BASE_URL = Config.BASE_URL

breeding_bp = Blueprint(
    "breeding", __name__, template_folder="templates", static_folder="static"
)


@breeding_bp.route("/egg-group/", defaults={"id_or_name": None})
@breeding_bp.route("/egg-group/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_egg_group(id_or_name):
    if id_or_name is None:
        # Fetch and render the list of all egg groups
        url = f"{BASE_URL}/egg-group"
        data = fetch_all_results(url)
        return render_template("egg_groups.html", data=data)
    else:
        try:
            # Check if id_or_name can be converted to an integer
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("egg-group", id_or_name)

            if "name" not in data:
                abort(404, description=f"Egg Group '{id_or_name}' not found")

            pokemon_list = build_pokemon_list(data.get("pokemon_species", []))

            # Fetch Summary
            summary = get_summary(data["name"], "egg-group")

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template(
                "egg_group_detail.html",
                data=data,
                pokemon_list=pokemon_list,
                summary_html=summary_html,
            )
        except ValueError as e:
            msg = str(e)
            if "not found" in msg.lower():
                abort(404, description=msg)
            abort(400, description=msg)



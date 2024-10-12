# routes/breeding.py
import logging
import markdown
import pandas as pd
from markupsafe import Markup
from flask import Blueprint, render_template, abort
from requests.exceptions import HTTPError

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results, create_pokemon_list, get_summary, get_path
from pokedex.utils import Config

breeding_bp = Blueprint("breeding", __name__, template_folder="templates", static_folder="static")


@breeding_bp.route("/egg-group/", defaults={"id_or_name": None})
@breeding_bp.route("/egg-group/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_egg_group(id_or_name):
    if id_or_name is None:
        # Fetch and render the list of all egg groups
        url = "https://pokeapi.co/api/v2/egg-group"
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

            # Use the create_pokemon_list function with the correct key
            pokemon_list = create_pokemon_list(data)

            # Fetch Summary
            csv_file_path = get_path('egg-group.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template(
                "egg_group_detail.html",
                data=data,
                pokemon_list=pokemon_list,
                summary_html=summary_html
            )
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@breeding_bp.route("/gender/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_gender(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("gender", id_or_name)

        if "name" not in data:
            abort(404, description=f"Gender '{id_or_name}' not found")

        return render_template("gender_detail.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status
    except HTTPError as e:
        # Handle HTTP errors, specifically 404
        if e.response.status_code == 404:
            abort(404, description=f"Gender '{id_or_name}' not found")
        else:
            logging.debug(f"HTTP error occurred: {e}")
            return str(e), e.response.status_code

# routes/characteristics_stats.py
import logging
import markdown
from flask import Blueprint, render_template, abort
from markupsafe import Markup
from requests.exceptions import HTTPError

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results, create_pokemon_list, get_path, get_summary, type_colors
from pokedex.utils import Config

characteristics_stats_bp = Blueprint("characteristics_stats", __name__, template_folder="templates",
                                     static_folder="static")


@characteristics_stats_bp.route("/characteristic/", defaults={"id_": None})
@characteristics_stats_bp.route("/characteristic/<int:id_>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_characteristic(id_):
    if id_ is None:
        # Fetch and display a list of all characteristics
        url = "https://pokeapi.co/api/v2/characteristic"
        data = fetch_all_results(url)

        # Extract the ID from the URL for each characteristic
        for characteristic in data:
            characteristic['id'] = int(characteristic['url'].split('/')[-2])

        return render_template("characteristics.html", data=data)
    else:
        # Fetch and display details for a specific characteristic
        try:
            data = pokedex.APIResource.fetch_data("characteristic", id_)

            if "id" not in data:
                abort(404, description=f"Characteristic '{id_}' not found")

            return render_template("characteristic_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status
        except HTTPError as e:
            # If the HTTP error is 404, raise a 404 Not Found
            if e.response.status_code == 404:
                abort(404, description=f"Characteristic '{id_}' not found")
            else:
                # For other HTTP errors, you might want to log them or handle differently
                logging.debug(f"HTTP error occurred: {e}")
                return str(e), e.response.status_code


@characteristics_stats_bp.route("/pokeathlon-stat/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_pokeathlon_stat(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("pokeathlon-stat", id_or_name)

        if "name" not in data:
            abort(404, description=f"Pokeathlon '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@characteristics_stats_bp.route("/stat/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_stat(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("stat", id_or_name)

        if "name" not in data:
            abort(404, description=f"Stat '{id_or_name}' not found")

        return render_template("stat_detail.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@characteristics_stats_bp.route("/type/", defaults={"id_or_name": None})
@characteristics_stats_bp.route("/type/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_type(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the types list
        url = "https://pokeapi.co/api/v2/type"
        types = fetch_all_results(url)
        return render_template("types.html", types=types)
    else:
        # id_or_name is provided, render the type detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("type", id_or_name)

            if "name" not in data:
                abort(404, description=f"Pokemon type '{id_or_name}' not found")

            pokemon_list = create_pokemon_list(data)

            # Fetch Summary
            csv_file_path = get_path('type.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template(
                "type_detail.html",
                type_effectiveness=data,
                pokemon_list=pokemon_list,
                type_colors=type_colors,
                summary_html=summary_html,
            )
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status

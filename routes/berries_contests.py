# routes/berries_contests.py
import logging
import pandas as pd
import markdown
from flask import Blueprint, render_template, abort
from markupsafe import Markup
from requests.exceptions import HTTPError

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results, get_summary, get_path
from pokedex.utils import Config

berries_contests_bp = Blueprint("berries_contests", __name__, template_folder="templates", static_folder="static")


@berries_contests_bp.route("/berry/", defaults={"id_or_name": None})
@berries_contests_bp.route("/berry/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_berry(id_or_name):
    if id_or_name is None:
        # Fetch and display a list of all berries
        url = "https://pokeapi.co/api/v2/berry"
        data = fetch_all_results(url)

        return render_template("berries.html", data=data)
    else:
        # Fetch and display details for a specific berry
        try:
            data = pokedex.APIResource.fetch_data("berry", id_or_name)

            if "name" not in data:
                abort(404, description=f"Berry '{id_or_name}' not found")

            # Fetch Summary
            csv_file_path = get_path('berry.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template("berry_detail.html", data=data, summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@berries_contests_bp.route("/berry-firmness/", defaults={"id_or_name": None})
@berries_contests_bp.route("/berry-firmness/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_berry_firmness(id_or_name):
    if id_or_name is None:
        # Fetch and display a list of all berry firmness categories
        url = "https://pokeapi.co/api/v2/berry-firmness"
        data = fetch_all_results(url)

        return render_template("berry_firmness.html", data=data)
    else:
        # Fetch and display details for a specific berry firmness
        try:
            data = pokedex.APIResource.fetch_data("berry-firmness", id_or_name)

            if "name" not in data:
                abort(404, description=f"Berry Firmness '{id_or_name}' not found")

            return render_template("berry_firmness_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@berries_contests_bp.route("/berry-flavor/", defaults={"id_or_name": None})
@berries_contests_bp.route("/berry-flavor/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_berry_flavor(id_or_name):
    if id_or_name is None:
        # Fetch and display a list of all berry flavors
        url = "https://pokeapi.co/api/v2/berry-flavor"
        data = fetch_all_results(url)

        return render_template("berry_flavors.html", data=data)
    else:
        # Fetch and display details for a specific berry flavor
        try:
            data = pokedex.APIResource.fetch_data("berry-flavor", id_or_name)

            if "name" not in data:
                abort(404, description=f"Berry Flavor '{id_or_name}' not found")

            return render_template("berry_flavor_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@berries_contests_bp.route("/contest-effect/", defaults={"id_": None})
@berries_contests_bp.route("/contest-effect/<int:id_>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_contest_effect(id_):
    if id_ is None:
        # Fetch and display a list of all contest effects
        url = "https://pokeapi.co/api/v2/contest-effect"
        data = fetch_all_results(url)

        # Extract the ID from the URL for each contest effect
        for effect in data:
            effect['id'] = int(effect['url'].split('/')[-2])

        return render_template("contest_effects.html", data=data)
    else:
        # Fetch and display details for a specific contest effect
        try:
            data = pokedex.APIResource.fetch_data("contest-effect", id_)

            if "id" not in data:
                abort(404, description=f"Contest '{id_}' not found")

            return render_template("contest_effect_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@berries_contests_bp.route("/contest-type/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_contest_type(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("contest-type", id_or_name)

        if "name" not in data:
            abort(404, description=f"Contest Type '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@berries_contests_bp.route("/super-contest-effect/<int:id_>")
def get_super_contest_effect(id_):
    try:
        data = pokedex.APIResource.fetch_data("super-contest-effect", id_)

        if "id" not in data:
            abort(404, description=f"Super Contest Effect '{id_}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status
    except HTTPError as e:
        # If the HTTP error is 404, raise a 404 Not Found
        if e.response.status_code == 404:
            abort(404, description=f"Super Contest Effect '{id_}' not found")
        else:
            # For other HTTP errors, you might want to log them or handle differently
            logging.debug(f"HTTP error occurred: {e}")
            return str(e), e.response.status_code
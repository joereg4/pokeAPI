# routes/locations_regions.py
import pandas as pd
import markdown
from flask import Blueprint, render_template, abort
from markupsafe import Markup
from requests.exceptions import HTTPError

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results, get_summary, get_path, create_pokemon_list
from pokedex.utils import Config

BASE_URL = Config.BASE_URL

locations_regions_bp = Blueprint("locations_regions", __name__, template_folder="templates", static_folder="static")


@locations_regions_bp.route("/location/", defaults={"id_or_name": None})
@locations_regions_bp.route("/location/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_location(id_or_name):
    if id_or_name is None:
        # Fetch all locations
        url = f"{BASE_URL}/location"
        data = fetch_all_results(url)
        return render_template("locations.html", data=data)
    else:
        try:
            # Check if id_or_name can be converted to an integer
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("location", id_or_name)

            if not data or "name" not in data:
                abort(404, description=f"Location '{id_or_name}' not found")

            return render_template("location_detail.html", data=data)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status
        except HTTPError as e:
            if e.response.status_code == 404:
                abort(404, description=f"Location '{id_or_name}' not found")
            else:
                return str(e), 500  # Internal Server Error for other issues


@locations_regions_bp.route("/location-area/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_location_area(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("location-area", id_or_name)

        if "name" not in data:
            abort(404, description=f"Location Area '{id_or_name}' not found")

        pokemon_list = create_pokemon_list(data)

        return render_template("location_area_detail.html", data=data, pokemon_list=pokemon_list)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@locations_regions_bp.route("/nature/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_nature(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("nature", id_or_name)

        if "name" not in data:
            abort(404, description=f"Nature '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@locations_regions_bp.route("/pal-park-area/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_pal_park_area(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("pal-park-area", id_or_name)

        if "name" not in data:
            abort(404, description=f"Pal Park Area '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@locations_regions_bp.route("/region/", defaults={"id_or_name": None})
@locations_regions_bp.route("/region/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_region(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the regions list
        url = f"{BASE_URL}/region"
        regions = fetch_all_results(url)
        return render_template("regions.html", regions=regions)
    else:
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("region", id_or_name)

            if "name" not in data:
                abort(404, description=f"Region '{id_or_name}' not found")

            # Fetch Summary
            csv_file_path = get_path('region.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            summary_html = Markup(markdown.markdown(summary)) if summary else None

            return render_template("region_detail.html", data=data, summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status

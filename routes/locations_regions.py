# routes/locations_regions.py
import pandas as pd
import markdown
from flask import Blueprint, render_template, abort
from markupsafe import Markup

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results, get_summary, get_path
from pokedex.services import build_pokemon_list
from pokedex.utils import Config
from routes.decorators import handle_api_errors

BASE_URL = Config.BASE_URL

locations_regions_bp = Blueprint(
    "locations_regions", __name__, template_folder="templates", static_folder="static"
)


@locations_regions_bp.route("/location/", defaults={"id_or_name": None})
@locations_regions_bp.route("/location/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Location")
def get_location(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/location"
        data = fetch_all_results(url)
        return render_template("locations.html", data=data)

    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("location", id_or_name)

    if not data or "name" not in data:
        abort(404, description=f"Location '{id_or_name}' not found")

    return render_template("location_detail.html", data=data)


@locations_regions_bp.route("/location-area/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Location Area")
def get_location_area(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("location-area", id_or_name)

    if "name" not in data:
        abort(404, description=f"Location Area '{id_or_name}' not found")

    pokemon_list = build_pokemon_list(data.get("pokemon_encounters", []))

    return render_template(
        "location_area_detail.html", data=data, pokemon_list=pokemon_list
    )


@locations_regions_bp.route("/region/", defaults={"id_or_name": None})
@locations_regions_bp.route("/region/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Region")
def get_region(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/region"
        regions = fetch_all_results(url)
        return render_template("regions.html", regions=regions)

    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("region", id_or_name)

    if "name" not in data:
        abort(404, description=f"Region '{id_or_name}' not found")

    summary = get_summary(data["name"], "region")
    summary_html = Markup(markdown.markdown(summary)) if summary else None

    return render_template(
        "region_detail.html", data=data, summary_html=summary_html
    )

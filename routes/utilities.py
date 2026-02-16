# utilities.py
import logging
import markdown
import pandas as pd
import sys
from flask import Blueprint, render_template, abort
from markupsafe import Markup

import pokedex
from cache import cache
from pokedex import fetch_all_results, get_path, get_summary
from pokedex.utils import Config
from routes.decorators import handle_api_errors

BASE_URL = Config.BASE_URL
utilities_bp = Blueprint("utilities", __name__, template_folder="templates")


@utilities_bp.route("/<api_endpoint>/<id_or_name>")
@handle_api_errors("Endpoint")
def get_endpoint_data(api_endpoint, id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    if api_endpoint in pokedex.__all__:
        try:
            func = getattr(sys.modules[__name__], api_endpoint)
            return func(id_or_name)
        except AttributeError:
            data = pokedex.APIResource.fetch_data(api_endpoint, id_or_name)
            return render_template(
                "generic.html", data=data, api_endpoint=api_endpoint
            )
    else:
        logging.warning(f"No such endpoint: {api_endpoint}")
        abort(404, description=f"No such endpoint: {api_endpoint}")


@utilities_bp.route("/encounter-method/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Encounter Method")
def get_encounter_method(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("encounter-method", id_or_name)

    if "name" not in data:
        abort(404, description=f"Encounter Method '{id_or_name}' not found")

    return render_template("encounter_method_detail.html", data=data)


@utilities_bp.route("/version/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Version")
def get_version(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("version", id_or_name)

    if "name" not in data:
        abort(404, description=f"Version '{id_or_name}' not found")

    summary = get_summary(data["name"], "version")
    summary_html = Markup(markdown.markdown(summary)) if summary else None

    return render_template(
        "version_detail.html", data=data, summary_html=summary_html
    )


@utilities_bp.route("/version-group/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Version Group")
def get_version_group(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("version-group", id_or_name)
    if "name" not in data:
        abort(404, description=f"Version Group '{id_or_name}' not found")

    summary = get_summary(data["name"], "version-group")
    summary_html = Markup(markdown.markdown(summary)) if summary else None

    return render_template(
        "version_group_detail.html", data=data, summary_html=summary_html
    )

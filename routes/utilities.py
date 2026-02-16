# utilities.py
import logging
import markdown
import pandas as pd
import sys
from flask import Blueprint, render_template, abort
from markupsafe import Markup
from werkzeug.exceptions import HTTPException

import pokedex
from cache import cache
from pokedex import fetch_all_results, get_path, get_summary
from pokedex.utils import Config

BASE_URL = Config.BASE_URL
utilities_bp = Blueprint("utilities", __name__, template_folder="templates")


def _handle_not_found(e):
    """Map ValueError to 404 when the message indicates a missing resource."""
    msg = str(e)
    if "not found" in msg.lower():
        abort(404, description=msg)
    abort(400, description=msg)


@utilities_bp.route("/<api_endpoint>/<id_or_name>")
def get_endpoint_data(api_endpoint, id_or_name):
    # Try to convert id_or_name to an integer, but keep it as a string if it fails
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # If conversion fails, id_or_name remains a string

    try:
        # Check if the api_endpoint exists in pokedex.__all__
        if api_endpoint in pokedex.__all__:
            # Prefer a dedicated view in this module if it exists (e.g. get_version, get_version_group)
            try:
                func = getattr(sys.modules[__name__], api_endpoint)
                return func(id_or_name)
            except AttributeError:
                # No dedicated view (e.g. hyphenated names); serve via generic fetch + template
                data = pokedex.APIResource.fetch_data(api_endpoint, id_or_name)
                return render_template(
                    "generic.html", data=data, api_endpoint=api_endpoint
                )
        else:
            # If the endpoint is not found, abort with a 404 error
            logging.warning(f"No such endpoint: {api_endpoint}")
            abort(404, description=f"No such endpoint: {api_endpoint}")
    except ValueError as e:
        _handle_not_found(e)
    except AttributeError:
        # Handle AttributeError in case the function is not found in the current module
        logging.error(f"Function for endpoint '{api_endpoint}' not found.")
        abort(404, description=f"Function for endpoint '{api_endpoint}' not found.")
    except HTTPException:
        # Re-raise HTTP exceptions (like abort(404)) without modification
        raise
    except Exception as e:
        # Handle any other exceptions and abort with a 500 Internal Server Error
        logging.exception(f"An unexpected error occurred: {str(e)}")
        abort(500, description="An unexpected error occurred")


@utilities_bp.route("/encounter-method/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_encounter_method(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass
    try:
        data = pokedex.APIResource.fetch_data("encounter-method", id_or_name)

        if "name" not in data:
            abort(404, description=f"Encounter Method '{id_or_name}' not found")

        return render_template("encounter_method_detail.html", data=data)
    except ValueError as e:
        _handle_not_found(e)


@utilities_bp.route("/version/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_version(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    try:
        data = pokedex.APIResource.fetch_data("version", id_or_name)

        if "name" not in data:
            abort(404, description=f"Version '{id_or_name}' not found")

        summary = get_summary(data["name"], "version")
        summary_html = Markup(markdown.markdown(summary)) if summary else None

        return render_template(
            "version_detail.html", data=data, summary_html=summary_html
        )
    except ValueError as e:
        _handle_not_found(e)


@utilities_bp.route("/version-group/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_version_group(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    try:
        data = pokedex.APIResource.fetch_data("version-group", id_or_name)
        if "name" not in data:
            abort(404, description=f"Version Group '{id_or_name}' not found")

        summary = get_summary(data["name"], "version-group")
        summary_html = Markup(markdown.markdown(summary)) if summary else None

        return render_template(
            "version_group_detail.html", data=data, summary_html=summary_html
        )
    except ValueError as e:
        _handle_not_found(e)

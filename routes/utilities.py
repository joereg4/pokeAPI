# utilities.py
import logging
import markdown
import pandas as pd
import sys
from flask import Blueprint, render_template, abort, json
from markupsafe import Markup

import pokedex
from cache import cache
from pokedex import fetch_all_results, get_path, get_summary
from pokedex.utils import Config, resources_dict

BASE_URL = Config.BASE_URL
utilities_bp = Blueprint("utilities", __name__, template_folder="templates")


@utilities_bp.errorhandler(ValueError)
def handle_value_error(error):
    # Log the error if needed
    logging.error(str(error))
    # Return a custom error message and a 400 Bad Request status code
    return str(error), 400


@utilities_bp.context_processor
def inject_resources():
    return dict(resources_json=json.dumps(resources_dict))


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
            # Dynamically fetch the function from the current module
            func = getattr(sys.modules[__name__], api_endpoint)
            data = func(id_or_name)
            return render_template("generic.html", data=data)
        else:
            # If the endpoint is not found, raise an appropriate error
            raise ValueError(f"No such endpoint: {api_endpoint}")
    except ValueError as e:
        # Handle ValueError and return a 400 Bad Request status with the error message
        return str(e), 400
    except AttributeError:
        # Handle AttributeError in case the function is not found in the current module
        return f"Function for endpoint '{api_endpoint}' not found.", 404
    except Exception as e:
        # Handle any other exceptions and return a 500 Internal Server Error
        return f"An error occurred: {str(e)}", 500


@utilities_bp.route("/encounter-condition/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_encounter_condition(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("encounter-condition", id_or_name)

        if "name" not in data:
            abort(404, description=f"Encounter Condition '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@utilities_bp.route("/encounter-condition_value/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_encounter_condition_value(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("encounter-condition-value", id_or_name)

        if "name" not in data:
            abort(404, description=f"Encounter Condition Value '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@utilities_bp.route("/encounter-method/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_encounter_method(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("encounter-method", id_or_name)

        if "name" not in data:
            abort(404, description=f"Encounter Method '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@utilities_bp.route("/language/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_language(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("language", id_or_name)

        if "name" not in data:
            abort(404, description=f"Language '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@utilities_bp.route("/version/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_version(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the versions list
        url = f"{BASE_URL}/version"
        data = fetch_all_results(url)
        return render_template("versions.html", data=data)
    else:
        # id_or_name is provided, render the version detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("version", id_or_name)

            if "name" not in data:
                abort(404, description=f"Version '{id_or_name}' not found")

            # Fetch Summary
            csv_file_path = get_path('version.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template("version_detail.html", data=data, summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@utilities_bp.route("/version-group/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
def get_version_group(id_or_name):
    if id_or_name is None:
        # No id_or_name provided, render the version groups list
        url = f"{BASE_URL}/version-group"
        data = fetch_all_results(url)
        return render_template("version_groups.html", data=data)
    else:
        # id_or_name is provided, render the version group detail
        try:
            id_or_name = int(id_or_name)
        except ValueError:
            pass  # if the conversion fails, it remains a string

        try:
            data = pokedex.APIResource.fetch_data("version-group", id_or_name)
            if "name" not in data:
                abort(404, description=f"Version Group '{id_or_name}' not found")

            # Fetch Summary
            csv_file_path = get_path('version-group.csv')
            df = pd.read_csv(csv_file_path)

            # Retrieve the summary
            summary = get_summary(data['name'], df)

            # Convert the markdown summary to HTML
            if summary:
                summary_html = Markup(markdown.markdown(summary))
            else:
                summary_html = None

            return render_template("version_group_detail.html", data=data, summary_html=summary_html)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status

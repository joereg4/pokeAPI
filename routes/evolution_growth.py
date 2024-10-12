# routes/evolution_growth.py
import logging
from flask import Blueprint, render_template, abort
from requests.exceptions import HTTPError

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results, create_pokemon_list

evolution_growth_bp = Blueprint("evolution_growth", __name__, template_folder="templates", static_folder="static")


@evolution_growth_bp.route("/evolution-chain/<int:id_>")
@cache.cached(timeout=300)
def get_evolution_chain(id_):
    try:
        data = pokedex.APIResource.fetch_data("evolution-chain", id_)

        if "id" not in data:
            abort(404, description=f"Evolution Chain '{id_}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status
    except HTTPError as e:
        # If the HTTP error is 404, raise a 404 Not Found
        if e.response.status_code == 404:
            abort(404, description=f"Evolution Chain '{id_}' not found")
        else:
            # For other HTTP errors, you might want to log them or handle differently
            logging.debug(f"HTTP error occurred: {e}")
            return str(e), e.response.status_code


@evolution_growth_bp.route("/evolution-trigger/<id_or_name>")
@cache.cached(timeout=300)
def get_evolution_trigger(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("evolution-trigger", id_or_name)

        if "name" not in data:
            abort(404, description=f"Evolution Trigger '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status


@evolution_growth_bp.route("/generation/", defaults={"id_or_name": None})
@evolution_growth_bp.route("/generation/<id_or_name>")
@cache.cached(timeout=300)
def get_generation(id_or_name):
    if id_or_name is None:
        # Fetch all generations
        url = "https://pokeapi.co/api/v2/generation"
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

            # Use the create_pokemon_list function with the correct key
            pokemon_list = create_pokemon_list(data)

            return render_template("generation_detail.html", data=data, pokemon_list=pokemon_list)
        except ValueError as e:
            return str(e), 400  # Return the error message with a 400 Bad Request status


@evolution_growth_bp.route("/growth-rate/<id_or_name>")
@cache.cached(timeout=300)
def get_growth_rate(id_or_name):
    # Check if id_or_name can be converted to an integer
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass  # if the conversion fails, it remains a string
    try:
        data = pokedex.APIResource.fetch_data("growth-rate", id_or_name)

        if "name" not in data:
            abort(404, description=f"Growth Rate '{id_or_name}' not found")

        return render_template("generic.html", data=data)
    except ValueError as e:
        return str(e), 400  # Return the error message with a 400 Bad Request status

# routes/berries_contests.py
import pandas as pd
import markdown
from flask import Blueprint, render_template, abort
from markupsafe import Markup

import pokedex
from cache import cache
from pokedex.helper import fetch_all_results, get_summary, get_path
from pokedex.utils import Config
from routes.decorators import handle_api_errors

BASE_URL = Config.BASE_URL

berries_contests_bp = Blueprint(
    "berries_contests", __name__, template_folder="templates", static_folder="static"
)


@berries_contests_bp.route("/berry/", defaults={"id_or_name": None})
@berries_contests_bp.route("/berry/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Berry")
def get_berry(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/berry"
        data = fetch_all_results(url)
        return render_template("berries.html", data=data)

    data = pokedex.APIResource.fetch_data("berry", id_or_name)

    if "name" not in data:
        abort(404, description=f"Berry '{id_or_name}' not found")

    summary = get_summary(data["name"], "berry")
    summary_html = Markup(markdown.markdown(summary)) if summary else None

    return render_template(
        "berry_detail.html", data=data, summary_html=summary_html
    )


@berries_contests_bp.route("/berry-firmness/", defaults={"id_or_name": None})
@berries_contests_bp.route("/berry-firmness/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Berry Firmness")
def get_berry_firmness(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/berry-firmness"
        data = fetch_all_results(url)
        return render_template("berry_firmness.html", data=data)

    data = pokedex.APIResource.fetch_data("berry-firmness", id_or_name)

    if "name" not in data:
        abort(404, description=f"Berry Firmness '{id_or_name}' not found")

    return render_template("berry_firmness_detail.html", data=data)


@berries_contests_bp.route("/berry-flavor/", defaults={"id_or_name": None})
@berries_contests_bp.route("/berry-flavor/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Berry Flavor")
def get_berry_flavor(id_or_name):
    if id_or_name is None:
        url = f"{BASE_URL}/berry-flavor"
        data = fetch_all_results(url)
        return render_template("berry_flavors.html", data=data)

    data = pokedex.APIResource.fetch_data("berry-flavor", id_or_name)

    if "name" not in data:
        abort(404, description=f"Berry Flavor '{id_or_name}' not found")

    return render_template("berry_flavor_detail.html", data=data)


@berries_contests_bp.route("/contest-effect/", defaults={"id_": None})
@berries_contests_bp.route("/contest-effect/<int:id_>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Contest Effect")
def get_contest_effect(id_):
    if id_ is None:
        url = f"{BASE_URL}/contest-effect"
        data = fetch_all_results(url)

        for effect in data:
            effect["id"] = int(effect["url"].split("/")[-2])

        return render_template("contest_effects.html", data=data)

    data = pokedex.APIResource.fetch_data("contest-effect", id_)

    if "id" not in data:
        abort(404, description=f"Contest '{id_}' not found")

    return render_template("contest_effect_detail.html", data=data)


@berries_contests_bp.route("/contest-type/<id_or_name>")
@cache.cached(timeout=Config.CACHE_TIMEOUT)
@handle_api_errors("Contest Type")
def get_contest_type(id_or_name):
    try:
        id_or_name = int(id_or_name)
    except ValueError:
        pass

    data = pokedex.APIResource.fetch_data("contest-type", id_or_name)

    if "name" not in data:
        abort(404, description=f"Contest Type '{id_or_name}' not found")

    return render_template("contest_type_detail.html", data=data)

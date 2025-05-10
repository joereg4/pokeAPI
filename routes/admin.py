from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models.model import User, db, Resource
from functools import wraps
from limiter import limiter
import requests
import logging

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You need admin privileges to access this page.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route("/dashboard")
@login_required
@admin_required
@limiter.limit("60 per minute")  # Allow 1 request per second for dashboard
def dashboard():
    users = User.query.all()
    return render_template("admin/dashboard.html", users=users)


@admin_bp.route("/users/add", methods=["GET", "POST"])
@login_required
@admin_required
@limiter.limit("30 per minute")  # More restrictive for user creation
def add_user():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        is_admin = request.form.get("is_admin") == "on"

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
            return redirect(url_for("admin.add_user"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists", "error")
            return redirect(url_for("admin.add_user"))

        user = User(username=username, email=email, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("User added successfully", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/add_user.html")


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
@limiter.limit("30 per minute")  # More restrictive for user editing
def edit_user(user_id):
    """Edit a user."""
    user = db.session.get(User, user_id)
    if not user:
        return render_template("404.html"), 404

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        is_admin = request.form.get("is_admin") == "on"
        password = request.form.get("password")

        if (
            username != user.username
            and User.query.filter_by(username=username).first()
        ):
            flash("Username already exists", "error")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        if email != user.email and User.query.filter_by(email=email).first():
            flash("Email already exists", "error")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        user.username = username
        user.email = email
        user.is_admin = is_admin
        if password:
            user.set_password(password)

        db.session.commit()
        flash("User updated successfully", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/edit_user.html", user=user)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = db.session.get(User, user_id)
    if not user:
        return render_template("404.html"), 404

    if user.id == current_user.id:
        flash("You cannot delete your own account", "error")
        return redirect(url_for("admin.dashboard"))

    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/list-pokemon-summaries", methods=["GET"])
@login_required
@admin_required
@limiter.limit("30 per minute")
def list_pokemon_summaries():
    """List all Pokemon with their summary status."""
    try:
        # Get all Pokemon resources from the database
        db_pokemon = Resource.query.filter_by(resource="pokemon").all()
        db_pokemon_names = {
            p.name: (
                p.summary is not None and p.summary.strip() != "" and p.summary != "NaN"
            )
            for p in db_pokemon
        }

        # Fetch all Pokemon from the PokeAPI
        all_pokemon_forms = []
        offset = 0
        limit = 500  # Fetch in chunks to avoid timeouts
        total_count = None

        # Keep fetching until we have all Pokemon
        while True:
            try:
                response = requests.get(
                    f"https://pokeapi.co/api/v2/pokemon?limit={limit}&offset={offset}"
                )
                if response.status_code != 200:
                    break

                data = response.json()
                if total_count is None:
                    total_count = data["count"]

                results = data.get("results", [])
                if not results:
                    break

                all_pokemon_forms.extend(results)
                offset += limit

                # If we've fetched all the Pokemon, break out
                if offset >= total_count:
                    break

            except Exception as e:
                logging.error(f"Error fetching Pokemon from offset {offset}: {str(e)}")
                break

        # Create a set of all Pokemon names from the API
        api_pokemon_names = {pokemon["name"] for pokemon in all_pokemon_forms}

        logging.info(f"Fetched {len(api_pokemon_names)} Pokemon from PokeAPI")

        # Create a full list of all Pokemon (both in API and DB)
        all_pokemon = []

        # First add all Pokemon from the API
        for name in api_pokemon_names:
            has_summary = db_pokemon_names.get(name, False)
            pokemon_info = {
                "name": name,
                "has_summary": has_summary,
                "display_name": name.replace("-", " ").title(),
            }
            all_pokemon.append(pokemon_info)

        # Add any Pokemon that might be in DB but not in API (unlikely but possible)
        for name, has_summary in db_pokemon_names.items():
            if name not in api_pokemon_names:
                pokemon_info = {
                    "name": name,
                    "has_summary": has_summary,
                    "display_name": name.replace("-", " ").title(),
                }
                all_pokemon.append(pokemon_info)

        # Sort by name
        all_pokemon.sort(key=lambda x: x["name"])

        # Filter if requested
        show_missing_only = request.args.get("missing_only", "false").lower() == "true"
        if show_missing_only:
            filtered_pokemon = [p for p in all_pokemon if not p["has_summary"]]
        else:
            filtered_pokemon = all_pokemon

        return render_template(
            "admin/list_pokemon_summaries.html",
            pokemon_list=filtered_pokemon,
            show_missing_only=show_missing_only,
            total_count=len(all_pokemon),
            missing_count=len([p for p in all_pokemon if not p["has_summary"]]),
        )

    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return render_template(
            "admin/list_pokemon_summaries.html",
            pokemon_list=[],
            show_missing_only=False,
            total_count=0,
            missing_count=0,
        )

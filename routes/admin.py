from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models.model import User, db, Resource
from functools import wraps
from limiter import limiter
import requests
import logging
from utils import invalidate_related_caches

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


@admin_bp.route(
    "/batch-refresh-summaries/<string:resource_type>", methods=["GET", "POST"]
)
@login_required
@admin_required
def batch_refresh_summaries(resource_type):
    """Batch refresh summaries for a specific resource type."""
    # Validate the resource type
    valid_resource_types = ["pokemon", "ability", "move", "item", "type"]
    if resource_type not in valid_resource_types:
        flash(f"Invalid resource type: {resource_type}", "error")
        return redirect(url_for("admin.dashboard"))

    # Handle form submission for batch refresh
    if request.method == "POST":
        try:
            import gc
            import time
            import psutil
            import os
            from datetime import datetime

            # Get the process to monitor memory usage
            process = psutil.Process(os.getpid())

            # Get batch processing parameters
            batch_size = int(request.form.get("batch_size", 10))
            delay_between_items = int(request.form.get("delay_between_items", 1))
            delay_between_batches = int(request.form.get("delay_between_batches", 5))
            log_memory_usage = request.form.get("log_memory_usage", "off") == "on"

            # Get the list of resource IDs to refresh
            resource_ids = request.form.getlist("resource_ids")

            if not resource_ids:
                flash("No resources selected for refresh", "warning")
                return redirect(
                    url_for(
                        "admin.batch_refresh_summaries", resource_type=resource_type
                    )
                )

            # Create batches
            batches = [
                resource_ids[i : i + batch_size]
                for i in range(0, len(resource_ids), batch_size)
            ]

            # Process count for progress tracking
            processed_count = 0
            total_count = len(resource_ids)
            error_count = 0

            # Log the start of the batch process
            logging.info(
                f"Starting batch refresh of {total_count} {resource_type} summaries with batch size {batch_size}"
            )
            if log_memory_usage:
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB
                logging.info(f"Initial memory usage: {initial_memory:.2f} MB")

            # Import the custom_generate_summary function
            from routes.summary_review import custom_generate_summary

            # Process each batch
            for batch_num, batch in enumerate(batches, 1):
                logging.info(
                    f"Processing batch {batch_num}/{len(batches)} with {len(batch)} items"
                )

                if log_memory_usage:
                    before_batch_memory = process.memory_info().rss / 1024 / 1024  # MB
                    logging.info(
                        f"Memory before batch {batch_num}: {before_batch_memory:.2f} MB"
                    )

                # Process each resource in the batch
                for item_num, resource_id in enumerate(batch, 1):
                    batch_start_time = datetime.now()
                    try:
                        # Check if this resource exists in the database
                        resource = Resource.query.filter_by(
                            resource=resource_type, name=resource_id
                        ).first()

                        # Generate a new summary
                        new_summary = custom_generate_summary(
                            resource_type=resource_type,
                            resource_name=resource_id,
                            base_summary="" if not resource else resource.summary,
                            max_tokens=2000,
                        )

                        # Create or update the resource in the database
                        if not resource:
                            resource = Resource(
                                resource=resource_type,
                                name=resource_id,
                                summary=new_summary,
                            )
                            db.session.add(resource)
                        else:
                            resource.summary = new_summary

                        # Save changes and invalidate cache
                        db.session.commit()
                        # Use the imported invalidate_related_caches
                        invalidate_related_caches(resource_type, resource_id)

                        processed_count += 1

                        # Log progress for each item
                        processing_time = (
                            datetime.now() - batch_start_time
                        ).total_seconds()
                        logging.info(
                            f"Processed {resource_type}/{resource_id} ({processed_count}/{total_count}) in {processing_time:.2f}s"
                        )

                    except Exception as e:
                        logging.error(
                            f"Error refreshing summary for {resource_type}/{resource_id}: {e}"
                        )
                        error_count += 1

                    # Add delay between items (if not the last item in the batch)
                    if item_num < len(batch) and delay_between_items > 0:
                        logging.info(f"Waiting {delay_between_items}s before next item")
                        time.sleep(delay_between_items)

                # Force garbage collection after each batch
                collected = gc.collect()

                if log_memory_usage:
                    after_batch_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_diff = after_batch_memory - before_batch_memory
                    logging.info(
                        f"Memory after batch {batch_num}: {after_batch_memory:.2f} MB (Change: {memory_diff:+.2f} MB)"
                    )
                    logging.info(f"Garbage collected {collected} objects")

                # Add delay between batches (if not the last batch)
                if batch_num < len(batches) and delay_between_batches > 0:
                    logging.info(f"Waiting {delay_between_batches}s before next batch")
                    time.sleep(delay_between_batches)

            # Log final memory usage if enabled
            if log_memory_usage:
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_diff = final_memory - initial_memory
                logging.info(
                    f"Final memory usage: {final_memory:.2f} MB (Total change: {memory_diff:+.2f} MB)"
                )

            # Provide feedback
            if error_count > 0:
                flash(
                    f"Refreshed {processed_count - error_count} summaries with {error_count} errors.",
                    "warning",
                )
            else:
                flash(
                    f"Successfully refreshed {processed_count} summaries for {resource_type}.",
                    "success",
                )

            return redirect(
                url_for("admin.batch_refresh_summaries", resource_type=resource_type)
            )

        except Exception as e:
            flash(f"Error during batch refresh: {str(e)}", "error")
            return redirect(
                url_for("admin.batch_refresh_summaries", resource_type=resource_type)
            )

    # GET request - display the form with resources to select
    try:
        # Fetch resources from appropriate API endpoint
        all_resources = []
        offset = 0
        limit = 100  # Fetch in batches

        # Keep fetching until we have all resources
        while True:
            try:
                endpoint = f"https://pokeapi.co/api/v2/{resource_type}?limit={limit}&offset={offset}"
                response = requests.get(endpoint)

                if response.status_code != 200:
                    break

                data = response.json()
                results = data.get("results", [])

                if not results:
                    break

                # Add resources to the list
                all_resources.extend(results)

                # Update offset for next batch
                offset += limit

                # If we've reached the end, break
                if offset >= data.get("count", 0):
                    break

            except Exception as e:
                logging.error(
                    f"Error fetching {resource_type} from offset {offset}: {str(e)}"
                )
                break

        # Get existing summaries from database
        db_resources = Resource.query.filter_by(resource=resource_type).all()
        db_resource_names = {
            r.name: (
                r.summary is not None and r.summary.strip() != "" and r.summary != "NaN"
            )
            for r in db_resources
        }

        # Prepare the resource list
        resources_list = []

        for resource in all_resources:
            name = resource["name"]
            has_summary = db_resource_names.get(name, False)

            resources_list.append(
                {
                    "name": name,
                    "display_name": name.replace("-", " ").title(),
                    "has_summary": has_summary,
                }
            )

        # Sort by name
        resources_list.sort(key=lambda x: x["name"])

        # Add statistics
        total_count = len(resources_list)
        missing_count = len([r for r in resources_list if not r["has_summary"]])

        return render_template(
            "admin/batch_refresh_summaries.html",
            resource_type=resource_type,
            resources_list=resources_list,
            total_count=total_count,
            missing_count=missing_count,
            resource_type_display=resource_type.title(),
        )

    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return render_template(
            "admin/batch_refresh_summaries.html",
            resource_type=resource_type,
            resources_list=[],
            total_count=0,
            missing_count=0,
            resource_type_display=resource_type.title(),
        )

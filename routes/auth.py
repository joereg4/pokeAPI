from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from datetime import datetime
from models.model import User, db
from limiter import limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(
    "5 per minute"
)  # Limit login attempts to 5 per minute to prevent brute force
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash("Logged in successfully!", "success")
            return redirect(url_for("admin.dashboard"))

        flash("Invalid username or password", "error")
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


def init_auth(app):
    """Initialize authentication for the app."""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "You must be logged in to access this page."
    login_manager.login_message_category = "error"

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.headers.get("Accept") == "application/json":
            return jsonify({"error": "Unauthorized"}), 401
        flash(login_manager.login_message, login_manager.login_message_category)
        return redirect(url_for("auth.login"))

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    return login_manager

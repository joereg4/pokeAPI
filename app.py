from flask import Flask
from routes import pokemon_bp
from database import get_db, close_db


def create_app():
    app = Flask(__name__)

    app.teardown_appcontext(close_db)
    app.register_blueprint(pokemon_bp)

    return app

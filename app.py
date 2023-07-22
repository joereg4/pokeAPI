from flask import Flask
from routes import pokemon_bp
from database import get_db, close_db
import logging
from dotenv import load_dotenv
import os

load_dotenv(".flaskenv")
print("Direct FLASK_ENV:", os.environ.get("FLASK_ENV"))


logging.basicConfig(level=logging.INFO)


def create_app():
    app = Flask(__name__)

    with app.app_context():
        get_db()

    app.teardown_appcontext(close_db)
    app.register_blueprint(pokemon_bp)


    for rule in app.url_map.iter_rules():
            logging.info(rule)

    return app

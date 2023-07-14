from flask import Flask
from routes import pokemon_bp
from database import get_db, close_db


def create_app():
    app = Flask(__name__)

    app.teardown_appcontext(close_db)
    app.register_blueprint(pokemon_bp)

    # print out all URL rules
    for rule in app.url_map.iter_rules():
        print(rule)

    return app

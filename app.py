from flask import Flask
from routes import pokemon_bp
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.register_blueprint(pokemon_bp)
    return app

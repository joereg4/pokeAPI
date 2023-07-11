from flask import Blueprint, render_template, request
from pokemon import Pokemon, get_pokemon_data, get_data

pokemon_bp = Blueprint(
    "pokemon", __name__, template_folder="templates", static_folder="static"
)


@pokemon_bp.route('/')
def index():
    pokemon_url = "https://pokeapi.co/api/v2/pokemon/?limit=20"
    pagination_url = pokemon_url

    pokemons, next_url = get_pokemon_data(pagination_url)
    return render_template('pokemon.html', pokemons=pokemons, next_url=next_url, prev_url=None)


@pokemon_bp.route('/page')
def page():
    page_url = request.args.get('url')
    pokemons, next_url = get_pokemon_data(page_url)
    return render_template('pokemon.html', pokemons=pokemons, next_url=next_url, prev_url=page_url)


@pokemon_bp.route('/next')
def next_page():
    next_url = request.args.get('url')
    pokemons, next_url = get_pokemon_data(next_url)
    return render_template('pokemon.html', pokemons=pokemons, next_url=next_url)

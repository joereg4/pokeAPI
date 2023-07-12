from flask import Blueprint, render_template, request
from pokemon import Pokemon, get_pokemon_data, get_data

pokemon_bp = Blueprint(
    "pokemon", __name__, template_folder="templates", static_folder="static"
)


@pokemon_bp.route('/')
def index():
    pokemon_url = "https://pokeapi.co/api/v2/pokemon/?limit=20"
    pokemons, next_url = get_pokemon_data(pokemon_url)
    return render_template('pokemon.html', pokemons=pokemons, next_url=next_url, prev_url=None)


@pokemon_bp.route('/page')
def page():
    current_page_url = request.args.get('url')
    pokemons, next_page_url = get_pokemon_data(current_page_url)
    return render_template('pokemon.html', pokemons=pokemons, next_url=next_page_url, prev_url=current_page_url)


@pokemon_bp.route('/next')
def next_page():
    next_page_url = request.args.get('url')
    pokemons, next_page_url_next = get_pokemon_data(next_page_url)
    return render_template('pokemon.html', pokemons=pokemons, next_url=next_page_url_next, prev_url=next_page_url)


@pokemon_bp.route('/prev')
def prev_page():
    prev_page_url = request.args.get('url')
    pokemons, _ = get_pokemon_data(prev_page_url)
    next_page_url = prev_page_url
    return render_template('pokemon.html', pokemons=pokemons, next_url=next_page_url, prev_url=prev_page_url)

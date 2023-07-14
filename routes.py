from flask import Blueprint, render_template, request, g
from pokemon import Pokemon, get_data
from database import get_db
import math

pokemon_bp = Blueprint(
    "pokemon", __name__, template_folder="templates", static_folder="static"
)


@pokemon_bp.route('/')
def index():
    db = get_db()
    collection = db['pokemon']

    page = int(request.args.get('page', 1))  # Get the current page number from the query parameters
    limit = 20  # Number of items per page

    # Calculate the offset based on the current page number and limit
    offset = (page - 1) * limit

    total_pokemons = collection.count_documents({})  # Total number of pokemons in the collection
    total_pages = math.ceil(total_pokemons / limit)  # Calculate the total number of pages

    # Get the pokemons for the current page using the offset and limit
    pokemons = collection.find().skip(offset).limit(limit)
    pokemons = list(pokemons)

    next_page = page + 1 if page < total_pages else None  # Calculate the next page number
    prev_page = page - 1 if page > 1 else None  # Calculate the previous page number

    next_url = f"/?page={next_page}" if next_page else None  # Construct the next page URL
    prev_url = f"/?page={prev_page}" if prev_page else None  # Construct the previous page URL

    return render_template('pokemon.html', pokemons=pokemons, next_url=next_url, prev_url=prev_url)


@pokemon_bp.route('/pokemon/<name>', methods=['GET'])
def get_pokemon(name):
    data = get_data(name.lower())
    if data is not None:
        return render_template('pokemon.html', data=data)
    else:
        return "Pokemon not found", 404

@pokemon_bp.route('/next')
def next_page():
    next_page_url = request.args.get('url')
    print(next_page_url)
    page_number = int(request.args.get('page', 1))  # Get the current page number from the query parameters
    print(page_number)
    next_page_number = page_number + 1
    print(next_page_number)

    db = get_db()
    collection = db['pokemon']

    limit = 20  # Number of items per page
    offset = (next_page_number - 1) * limit  # Calculate the offset based on the next page number

    total_pokemons = collection.count_documents({})  # Total number of pokemons in the collection
    total_pages = math.ceil(total_pokemons / limit)  # Calculate the total number of pages

    # Check if the next page number is within the valid range
    if next_page_number <= total_pages:
        # Get the pokemons for the next page using the offset and limit
        pokemons = collection.find().skip(offset).limit(limit)
        pokemons = list(pokemons)

        next_url = f"/next?url={next_page_url}"  # Construct the URL for the next page
        prev_url = f"/?page={page_number}" if page_number > 1 else None  # Construct the URL for the previous page
    else:
        # The next page number is out of range, so set the values to None
        pokemons = []
        next_url = None
        prev_url = f"/?page={page_number}" if page_number > 1 else None  # Construct the URL for the previous page

    return render_template('pokemon.html', pokemons=pokemons, next_url=next_url, prev_url=prev_url)










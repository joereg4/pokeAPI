import logging

from flask import Blueprint, render_template, request, g
from pokemon import Pokemon
from database import get_db
import requests
import math

logging.basicConfig(level=logging.INFO)

pokemon_bp = Blueprint(
    "pokemon", __name__, template_folder="templates", static_folder="static"
)

pokeapi_base_url = 'https://pokeapi.co/api/v2/'


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


@pokemon_bp.route('/pokemon/<name>')
def get_pokemon(name):
    db = get_db()
    collection = db['pokemon']

    pokemon = collection.find_one({"name": name.lower()})
    print(pokemon)
    if pokemon is not None:
        data = {
            'name': pokemon['name'].title(),
            'id': pokemon['id'],
            'sprites': pokemon['sprites'],
            'species': pokemon['species'],
            'base_experience': pokemon['base_experience'],
            'height': pokemon['height'],
            'weight': pokemon['weight'],
            'is_default': pokemon['is_default'],
            'order': pokemon['order'],
            'abilities': pokemon.get('abilities', []),
            'moves': pokemon.get('moves', []),
            'held_items': pokemon.get('held_items', [])
        }

        # Define the valid sprite names to filter
        valid_sprites = ['front_default', 'back_default', 'front_female', 'back_female', 'front_shiny', 'back_shiny',
                         'front_shiny_female', 'back_shiny_female'
                         ]

        # Get the sprite data and filter out null values and unwanted sprites
        sprites = {
            key: value for key, value in pokemon['sprites'].items()
            if value is not None and key in valid_sprites
        }

        # Sort the sprites based on the desired order
        sorted_sprites = {key: sprites[key] for key in valid_sprites if key in sprites}

        # Sort the sprites based on the desired order
        sorted_sprites = {key: sprites[key] for key in valid_sprites if key in sprites}

        # Get the evolution chain using the species url
        species_id = pokemon['species']['url'].replace('https://pokeapi.co/api/v2/pokemon-species/', '').strip('/')
        evolution_chain = Pokemon.get_evolution_chain(species_id)

        return render_template('pokemon_detail.html', data=data, sprites=sorted_sprites,
                               evolution_chain=evolution_chain)
    else:
        return "Pokemon not found", 404


@pokemon_bp.route('/ability/<int:ability_id>')
def get_ability_data(ability_id):
    response = requests.get(f'https://pokeapi.co/api/v2/ability/{ability_id}')
    if response.status_code == 200:
        data = response.json()

        # Filter for English language data
        data['effect_entries'] = [entry for entry in data['effect_entries'] if entry['language']['name'] == 'en']
        data['flavor_text_entries'] = [entry for entry in data['flavor_text_entries'] if
                                       entry['language']['name'] == 'en']

        return render_template('pokemon_ability.html', data=data)
    else:
        return "Ability not found", 404


@pokemon_bp.route('/move/<int:move_id>')
def get_move_data(move_id):
    response = requests.get(f'https://pokeapi.co/api/v2/move/{move_id}')
    if response.status_code == 200:
        data = response.json()
        return render_template('pokemon_move.html', data=data)
    else:
        return "Move not found", 404


@pokemon_bp.route('/item/<id_or_name>')
def get_item_data(id_or_name):
    response = requests.get(f'https://pokeapi.co/api/v2/item/{id_or_name}')
    if response.status_code == 200:
        data = response.json()

        # Filter for English language data
        data['effect_entries'] = [entry for entry in data['effect_entries'] if entry['language']['name'] == 'en']
        data['flavor_text_entries'] = [entry for entry in data['flavor_text_entries'] if
                                       entry['language']['name'] == 'en']
        return render_template('pokemon_item.html', data=data)
    else:
        return "Item not found", 404


@pokemon_bp.route('/pokemon/<id_or_name>/encounters')
def get_encounter_data(id_or_name):
    print("Accessing encounters for:", id_or_name)
    response = requests.get(f'https://pokeapi.co/api/v2/pokemon/{id_or_name}/encounters/')
    print(f'Response from PokeAPI: {response.status_code}')

    if response.status_code == 200:
        data = response.json()

        return render_template('pokemon_encounter.html', data=data)
    else:
        return "Encounter not found", 404


@pokemon_bp.route('/species/<id_or_name>')
def get_species_data(id_or_name):
    response = requests.get(f'https://pokeapi.co/api/v2/pokemon-species/{id_or_name}')
    print(f'https://pokeapi.co/api/v2/pokemon-species/{id_or_name}')
    if response.status_code == 200:
        data = response.json()

        data = Pokemon.filter_english_data(data, ['names', 'effect_entries', 'flavor_text_entries'])

        return render_template('pokemon_species.html', data=data)
    else:
        return "Species not found", 404


@pokemon_bp.route('/<api_endpoint>/<int:id>')
def get_endpoint_data(api_endpoint, id):
    full_url = f"{pokeapi_base_url}/{api_endpoint}/{id}"
    response = requests.get(full_url)

    if response.status_code == 200:
        data = response.json()

        # Filter for English language data if 'effect_entries' field exists
        effect_entries = data.get('effect_entries', [])
        data['effect_entries'] = [entry for entry in effect_entries if entry.get('language', {}).get('name') == 'en']

        # Filter for English language data if 'flavor_text_entries' field exists
        flavor_text_entries = data.get('flavor_text_entries', [])
        data['flavor_text_entries'] = [entry for entry in flavor_text_entries if
                                       entry.get('language', {}).get('name') == 'en']

        return render_template('generic.html', data=data)
    else:
        return "Endpoint not found", 404


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

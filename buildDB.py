import requests
import os
from pymongo import MongoClient
from pokemon import Pokemon
from dotenv import load_dotenv

load_dotenv()

# MongoDB Setup
client = MongoClient(os.environ.get("MONGODB_URI"))
db = client['pokemon_db']  # replace 'your_database_name' with your database name

# Define the collection
collection = db['pokemon']

def get_pokemon_data():
    base_url = 'https://pokeapi.co/api/v2/pokemon?limit=100'  # URL to get all pokemon.
    # If you only want first 151, change limit to 151
    while base_url:
        response = requests.get(base_url)
        data = response.json()
        for result in data['results']:
            pokemon_response = requests.get(result['url'])
            pokemon_data = pokemon_response.json()
            pokemon = Pokemon(pokemon_data)  # Use your Pokemon class to parse the data
            yield pokemon.to_dict()  # Return a dictionary representation of the Pokemon
        base_url = data['next']  # Get the next page of Pokemon

def populate_db():
    for pokemon in get_pokemon_data():
        collection.insert_one(pokemon)
        print(f'Inserted {pokemon["name"]} into the database.')

if __name__ == "__main__":
    populate_db()

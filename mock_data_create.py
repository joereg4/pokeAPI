import os
import json
import requests

# Base URL of the PokeAPI
POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/"

# Directory to save the mock data
MOCK_DATA_DIR = "mock_data"


def fetch_and_save_data(endpoint, id_or_name, filename):
    """Fetch data from the PokeAPI and save it to a JSON file."""
    url = f"{POKEAPI_BASE_URL}{endpoint}/{id_or_name}/"
    print(f"Fetching data from: {url}")

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()

        # Ensure the mock_data directory exists
        os.makedirs(MOCK_DATA_DIR, exist_ok=True)

        # Save the data to a JSON file
        filepath = os.path.join(MOCK_DATA_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

        print(f"Saved mock data to {filepath}")

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")


def fetch_pokemon_data(pokemon_name):
    """Fetch and save data for a given Pokémon."""
    # Fetch Pokémon data
    fetch_and_save_data("pokemon", pokemon_name, f"{pokemon_name}.json")

    # Fetch Pokémon species data
    fetch_and_save_data("pokemon-species", pokemon_name, f"{pokemon_name}_species.json")


def fetch_type_data(pokemon_name):
    """Fetch and save type data for a Pokémon."""
    # Fetch Pokémon data first to get its types
    pokemon_url = f"{POKEAPI_BASE_URL}pokemon/{pokemon_name}/"
    response = requests.get(pokemon_url)
    response.raise_for_status()
    pokemon_data = response.json()

    # Fetch data for each type of the Pokémon
    for type_info in pokemon_data.get("types", []):
        type_name = type_info["type"]["name"]
        fetch_and_save_data("type", type_name, f"{type_name}_type.json")


def fetch_evolution_chain(pokemon_name):
    """Fetch and save evolution chain data for a given Pokémon."""
    # Fetch Pokémon species data to get the evolution chain URL
    species_url = f"{POKEAPI_BASE_URL}pokemon-species/{pokemon_name}/"
    response = requests.get(species_url)
    response.raise_for_status()
    species_data = response.json()

    evolution_chain_url = species_data["evolution_chain"]["url"]
    evolution_chain_id = evolution_chain_url.split('/')[-2]  # Extract the ID from the URL

    # Fetch evolution chain data
    fetch_and_save_data("evolution-chain", evolution_chain_id, f"{pokemon_name}_evolution_chain.json")


def fetch_ability_data(ability_name):
    """Fetch and save data for a given ability."""
    # Fetch ability data
    fetch_and_save_data("ability", ability_name, f"{ability_name}.json")



def main():
    # Specify the Pokémon you want to fetch data for
    pokemon_name = "bulbasaur"

    # Fetch and save data for the Pokémon
    fetch_pokemon_data(pokemon_name)

    # Fetch and save type data for the Pokémon
    fetch_type_data(pokemon_name)

    # Fetch and save evolution chain data for the Pokémon
    fetch_evolution_chain(pokemon_name)

    fetch_ability_data('stench')


if __name__ == "__main__":
    main()

# pokedex/helper.py
import logging
import requests
import os
from flask import url_for, current_app
from pokemontcgsdk import Card
import pokedex
from pokedex.utils import Config

VALID_SPRITES = Config.VALID_SPRITES
TYPE_COLORS = Config.TYPE_COLORS


def get_path(filename):
    csv_url = url_for('static', filename=f'resources/{filename}')
    csv_path = os.path.join(current_app.root_path, csv_url.lstrip('/'))
    return csv_path


def get_summary(name, df):
    row = df[(df['name'].str.lower() == name.lower())]
    if not row.empty:
        return row.iloc[0]['summary']
    else:
        return None


def get_pokemon_cards(name):
    try:
        # Attempt to fetch the cards using the API
        data = pokedex.Card.where(q='name:{}'.format(name))

        card_list = []
        for card in data:
            card_list.append({
                'id': card.id,
                'name': card.name,
                'artist': card.artist,
                'large_image': card.images.large,
                'set_name': card.set.name
            })
        return card_list

    except Exception as e:
        # Log the exception for debugging purposes
        logging.error(f"Error fetching Pokémon cards for {name}: {e}")
        return []  # Return an empty list on error


def create_pokemon_list(data):
    try:
        # If data is a list, assume it contains the Pokémon entries directly
        if isinstance(data, list):
            pokemon_entries = data
            key = "list"  # To avoid issues if a key is needed later
        else:
            # Possible keys that might contain the Pokémon species list
            possible_keys = ["pokemon", "pokemon_species", "pokemon_entries", "pokemon_encounters", "held_by_pokemon",
                             "learned_by_pokemon", "varieties", "detective"]

            # Identify the correct key by checking which one exists in the data
            key = next((k for k in possible_keys if k in data), None)

            if not key:
                raise ValueError("No valid key found in data for Pokémon list.")

            # Assign the Pokémon entries based on the identified key
            if key == "pokemon_entries":
                pokemon_entries = [entry["pokemon_species"] for entry in data[key]]
            else:
                pokemon_entries = data[key]

        # Build the Pokémon list based on the identified key
        pokemon_list = []
        for pokemon_entry in pokemon_entries:

            # If we have species data, fetch Pokémon from the species
            if key == "pokemon_species" and "name" in pokemon_entry:
                species_name = pokemon_entry["name"]
                species_data = pokedex.APIResource.fetch_data("pokemon-species", species_name)

                # Recursive call to handle all Pokémon in the species
                species_pokemon_list = create_pokemon_list(species_data["varieties"])
                pokemon_list.extend(species_pokemon_list)

                # Now handle the species-specific entry number and artwork
                entry_number = species_data.get('pokedex_numbers', [{}])[0].get('entry_number', None)
                for pokemon in species_pokemon_list:
                    # Append the entry number and official artwork to each Pokémon in the species
                    pokemon['entry_number'] = entry_number
                    pokemon['official_artwork'] = pokedex.get_official_artwork(
                        pokemon['name'],
                        pokemon['sprites'].get('other', {}).get('official-artwork', {}).get('front_default'),
                        entry_number
                    )
                continue

            # The key structure is different depending on the data source
            if isinstance(pokemon_entry, dict):
                pokemon_name = pokemon_entry["name"] if "name" in pokemon_entry else pokemon_entry.get("pokemon",
                                                                                                       {}).get("name")
            else:
                logging.debug(f"Warning: Invalid Pokémon entry structure under key '{key}': {pokemon_entry}")
                continue

            if not pokemon_name:
                logging.debug(f"Warning: Could not find Pokémon name in entry under key '{key}': {pokemon_entry}")
                continue

            # Fetch the Pokémon data
            pokemon = pokedex.APIResource.fetch_data("pokemon", pokemon_name)

            # Add encounter details if available
            if key == "pokemon_encounters":
                version_details = pokemon_entry.get("version_details", [])
                pokemon['version_details'] = []

                for version_detail in version_details:
                    encounter_info = {
                        'version_name': version_detail['version']['name'],
                        'method': version_detail['encounter_details'][0]['method']['name'],
                        'max_level': version_detail['encounter_details'][0]['max_level'],
                        'min_level': version_detail['encounter_details'][0]['min_level'],
                        'chance': version_detail['encounter_details'][0]['chance']
                    }
                    pokemon['version_details'].append(encounter_info)

            # Check if the 'sprites' key exists in the Pokémon data
            if "sprites" in pokemon:
                # Get the official artwork or use a fallback if not available
                official_artwork = pokemon['sprites'].get('other', {}).get('official-artwork', {}).get('front_default')
                entry_number = pokemon.get('entry_number')  # We ensure entry_number is required
                if entry_number is None:
                    official_artwork = official_artwork
                else:
                    official_artwork = pokedex.get_official_artwork(pokemon_name, official_artwork, entry_number)
                # Add the official artwork to the Pokémon data
                pokemon['official_artwork'] = official_artwork
                # Add Pokémon to the list
                # Append the Pokémon with only required data
                pokemon_list.append({
                    "name": pokemon_name,
                    "official_artwork": official_artwork,
                    "id": pokemon.get("id"),
                    "types": pokemon.get("types", []),
                    "sprites": pokemon.get("sprites", {}),
                })
            else:
                logging.debug(f"No sprites found for Pokémon '{pokemon_name}' under key '{key}'")

        # Sort the Pokémon list only if the key is not "detective"
        if key != "detective":
            pokemon_list.sort(key=lambda x: x.get("id", float("inf")))

        return pokemon_list
    except ValueError as e:
        logging.error(f"Error fetching Pokémon data under key '{key}': {e}")
        return []


def fetch_all_results(url):
    results = []
    while url:
        response = requests.get(url)
        data = response.json()
        results.extend(data["results"])
        url = data.get("next")  # Get the next page URL, if it exists
    return results

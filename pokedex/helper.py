# pokedex/helper.py
import logging
import requests
import os
from flask import url_for, current_app
from pokemontcgsdk import Card
import pokedex
from pokedex.utils import Config
from models.model import Resource, db
from pokedex.sprite import get_sprite_url

VALID_SPRITES = Config.VALID_SPRITES
TYPE_COLORS = Config.TYPE_COLORS


def get_path(filename):
    csv_url = url_for("static", filename=f"resources/{filename}")
    csv_path = os.path.join(current_app.root_path, csv_url.lstrip("/"))
    return csv_path


def get_summary(name, resource_type):
    """Get summary from the database for a given resource name and type."""
    resource = (
        db.session.query(Resource)
        .filter(
            db.and_(Resource.name == name.lower(), Resource.resource == resource_type)
        )
        .first()
    )

    return resource.summary if resource else None


def get_pokemon_cards(name):
    try:
        # Attempt to fetch the cards using the API
        data = pokedex.Card.where(q="name:{}".format(name))

        card_list = []
        for card in data:
            card_list.append(
                {
                    "id": card.id,
                    "name": card.name,
                    "artist": card.artist,
                    "large_image": card.images.large,
                    "set_name": card.set.name,
                }
            )
        return card_list

    except Exception as e:
        # Log the exception for debugging purposes
        logging.error(f"Error fetching Pokémon cards for {name}: {e}")
        return []  # Return an empty list on error


def create_pokemon_list(data):
    """Create a list of Pokémon with their details."""
    pokemon_list = []
    entries = []

    # Handle different data structures
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        if "results" in data:
            entries = data["results"]
        elif "pokemon" in data:
            entries = data["pokemon"]
        elif "pokemon_species" in data:
            entries = data["pokemon_species"]
        else:
            logging.error("Unexpected data structure for Pokémon list")
            return []

    for entry in entries:
        try:
            # Extract the Pokémon name from the entry
            if isinstance(entry, dict):
                pokemon_name = (
                    entry["name"]
                    if "name" in entry
                    else entry.get("pokemon", {}).get("name")
                )
            else:
                logging.warning(f"Invalid Pokémon entry structure: {entry}")
                continue

            if pokemon_name:
                # Fetch the Pokémon data
                pokemon = pokedex.APIResource.fetch_data("pokemon", pokemon_name)
                if pokemon and "sprites" in pokemon:
                    # Get artwork URL
                    try:
                        if pokemon.get("id"):
                            official_artwork = get_sprite_url(
                                pokemon["id"], is_artwork=True
                            )
                        else:
                            official_artwork = None
                    except Exception as e:
                        logging.warning(
                            f"Error getting artwork URL for {pokemon_name}: {e}"
                        )
                        official_artwork = None

                    # Add to list
                    pokemon_list.append(
                        {
                            "name": pokemon_name,
                            "official_artwork": official_artwork,
                            "id": pokemon.get("id"),
                            "types": pokemon.get("types", []),
                            "sprites": pokemon.get("sprites", {}),
                        }
                    )
                else:
                    logging.warning(f"No sprite data found for {pokemon_name}")
        except Exception as e:
            logging.error(f"Error processing Pokémon {entry}: {e}")
            continue

    return sorted(pokemon_list, key=lambda x: x.get("id", float("inf")))


def fetch_all_results(url):
    results = []
    while url:
        response = requests.get(url)
        data = response.json()
        results.extend(data["results"])
        url = data.get("next")  # Get the next page URL, if it exists
    return results

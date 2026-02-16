# pokedex/helper.py
import logging
import os

from flask import url_for, current_app
from pokedex.utils import Config
from models.model import Resource, db

TCG_API_TIMEOUT = Config.TCG_API_TIMEOUT


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
    """
    Fetch Pokemon trading cards from local database.
    Uses the imported TCG data for reliable, fast card lookups.
    """
    try:
        from models.tcg_card import TcgCard

        logging.info(f"Searching local database for Pokemon cards: {name}")

        # Try multiple search strategies
        cards = []

        # Strategy 1: Direct name match (most accurate)
        cards = TcgCard.find_by_name(name)
        if cards:
            logging.info(f"Found {len(cards)} cards by name search for '{name}'")

        # Strategy 2: If no results, try by Pokedex number for known Pokemon
        if not cards:
            pokemon_pokedex_map = {
                "pikachu": 25,
                "charizard": 6,
                "blastoise": 9,
                "venusaur": 3,
                "mewtwo": 150,
                "mew": 151,
                "lugia": 249,
                "ho-oh": 250,
                "rayquaza": 384,
                "arceus": 493,
            }

            if name.lower() in pokemon_pokedex_map:
                pokedex_num = pokemon_pokedex_map[name.lower()]
                cards = TcgCard.find_by_pokedex_number(pokedex_num)
                if cards:
                    logging.info(
                        f"Found {len(cards)} cards by Pokedex number {pokedex_num} for '{name}'"
                    )

        # Strategy 3: If still no results, try by type for known Pokemon
        if not cards:
            type_map = {
                "pikachu": "Lightning",
                "charizard": "Fire",
                "blastoise": "Water",
                "venusaur": "Grass",
            }

            if name.lower() in type_map:
                pokemon_type = type_map[name.lower()]
                cards = TcgCard.find_by_type(pokemon_type)
                if cards:
                    logging.info(
                        f"Found {len(cards)} cards by type {pokemon_type} for '{name}'"
                    )

        # Convert to the expected format
        if cards:
            card_list = []
            for card in cards:
                card_dict = card.to_dict()
                card_list.append(card_dict)

            logging.info(
                f"Returning {len(card_list)} cards for '{name}' from local database"
            )
            return card_list
        else:
            logging.info(f"No Pokemon cards found for '{name}' in local database")
            return []

    except ImportError:
        logging.error("TcgCard model not available - database may not be set up")
        return []
    except Exception as e:
        # Log the exception for debugging purposes
        logging.error(
            f"Error fetching Pokémon cards for {name} from database: {str(e)}"
        )
        return []  # Return an empty list on error


def create_pokemon_list(data):
    """Create a list of Pokemon with their details.

    .. deprecated:: Use pokedex.services.build_pokemon_list() instead.
       This wrapper exists for backward compatibility.
    """
    from pokedex.services import build_pokemon_list
    return build_pokemon_list(data)


def fetch_all_results(url):
    """Follow pagination links to collect all results from a PokéAPI list."""
    from .client import client
    return client.fetch_all_pages(url)



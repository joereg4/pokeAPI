# pokedex/helper.py
import logging
import os

from flask import url_for, current_app
from pokemontcgsdk import Card
import pokedex
from pokedex.utils import Config
from models.model import Resource, db
from pokedex.sprite import get_sprite_url
import ssl
import urllib.request
import urllib.error
import json

from pokedex.serializers import serialize_pokemon_list_entry

VALID_SPRITES = Config.VALID_SPRITES
TYPE_COLORS = Config.TYPE_COLORS
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
                # Try to fetch the Pokémon data first
                pokemon = None
                try:
                    pokemon = pokedex.APIResource.fetch_data("pokemon", pokemon_name)

                    # If Pokémon was found but has None ID, try species data fallback
                    if pokemon and pokemon.get("id") is None:
                        variety_name = get_default_variety_name(pokemon_name)
                        if variety_name:
                            try:
                                variety_pokemon = pokedex.APIResource.fetch_data(
                                    "pokemon", variety_name
                                )
                                if (
                                    variety_pokemon
                                    and variety_pokemon.get("id") is not None
                                ):
                                    pokemon = variety_pokemon
                                else:
                                    logging.warning(
                                        f"Default variety '{variety_name}' also has None ID"
                                    )
                            except Exception as e:
                                logging.warning(
                                    f"Failed to fetch default variety '{variety_name}' for '{pokemon_name}': {e}"
                                )

                except ValueError as e:
                    # Pokémon not found, try to get default variety
                    variety_name = get_default_variety_name(pokemon_name)
                    if variety_name:
                        try:
                            pokemon = pokedex.APIResource.fetch_data(
                                "pokemon", variety_name
                            )
                        except Exception as e:
                            logging.warning(
                                f"Failed to fetch default variety '{variety_name}' for '{pokemon_name}': {e}"
                            )

                if pokemon:
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

                    # Add to list (serialize to guarantee template safety)
                    pokemon_data = serialize_pokemon_list_entry({
                        "name": pokemon_name,
                        "official_artwork": official_artwork,
                        "id": pokemon.get("id"),
                        "types": pokemon.get("types", []),
                        "sprites": pokemon.get("sprites", {}),
                        "is_variety": pokemon.get("name") != pokemon_name,
                        "variety_name": (
                            pokemon.get("name")
                            if pokemon.get("name") != pokemon_name
                            else None
                        ),
                    })
                    pokemon_list.append(pokemon_data)
                else:
                    logging.warning(
                        f"No data found for {pokemon_name} (including default variety)"
                    )
        except Exception as e:
            logging.error(f"Error processing Pokémon {entry}: {e}")
            continue

    return sorted(
        pokemon_list,
        key=lambda x: x.get("id") if x.get("id") is not None else float("inf"),
    )


def fetch_all_results(url):
    """Follow pagination links to collect all results from a PokéAPI list."""
    from .client import client
    return client.fetch_all_pages(url)


def get_default_variety_name(pokemon_name):
    """
    When a Pokémon name returns 404, try to get the default variety name from species data.
    Assumes every species has an is_default=true variety.
    Returns the variety name (e.g., 'wormadam-plant') or None if not found.
    """
    try:
        # Fetch species data
        species_data = pokedex.APIResource.fetch_data("pokemon-species", pokemon_name)

        if species_data and "varieties" in species_data and species_data["varieties"]:
            # Find the default variety (is_default=true)
            for variety in species_data["varieties"]:
                if variety.get("is_default", False):
                    variety_name = variety["pokemon"]["name"]
                    return variety_name

            logging.warning(f"No default variety found for '{pokemon_name}'")
        else:
            logging.warning(f"No varieties found for '{pokemon_name}'")

        return None

    except Exception as e:
        logging.warning(f"Error fetching species data for '{pokemon_name}': {e}")
        return None

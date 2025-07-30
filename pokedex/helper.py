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
import ssl
import urllib.request
import urllib.error
import json

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
    Fetch Pokemon trading cards with improved error handling and timeout.
    Uses Pokemon TCG API with optional API key authentication.
    The Pokemon TCG API is often slow/unreliable, so we use aggressive timeouts.
    """
    try:
        # Check for API key in environment variables
        api_key = os.getenv("POKEMONTCG_IO_API_KEY")

        # Use aggressive timeout (from config) since Pokemon TCG API is very slow
        # Try exact name match first, then fallback to partial match
        search_queries = [
            f'name:"{name}"',  # Exact match with quotes
            f"name:{name}",  # Simple match
        ]

        for query in search_queries:
            try:
                url = f"https://api.pokemontcg.io/v2/cards?q={query}&pageSize=10"

                # Create SSL context that works on macOS
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                # Create request with API key if available
                req = urllib.request.Request(url)
                if api_key:
                    req.add_header("X-Api-Key", api_key)
                    logging.debug(f"Pokemon TCG API configured with API key")
                else:
                    logging.debug(
                        "No Pokemon TCG API key found, using unauthenticated requests"
                    )

                # Make the API call with aggressive timeout
                with urllib.request.urlopen(
                    req, context=ssl_context, timeout=TCG_API_TIMEOUT
                ) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())

                        card_list = []
                        for card in data.get("data", []):
                            # Handle missing fields gracefully
                            images = card.get("images", {})
                            set_info = card.get("set", {})

                            card_list.append(
                                {
                                    "id": card.get("id", ""),
                                    "name": card.get("name", ""),
                                    "artist": card.get("artist", "Unknown"),
                                    "large_image": images.get("large", ""),
                                    "set_name": set_info.get("name", "Unknown Set"),
                                }
                            )

                        if card_list:
                            logging.debug(
                                f"Found {len(card_list)} cards for {name} with query: {query}"
                            )
                            return card_list
                        else:
                            logging.debug(
                                f"No cards found for {name} with query: {query}, trying next query..."
                            )
                            continue
                    else:
                        logging.warning(
                            f"Pokemon TCG API returned status {response.status} for {name}"
                        )
                        continue

            except urllib.error.HTTPError as e:
                if e.code == 504:
                    logging.warning(
                        f"Pokemon TCG API gateway timeout for query: {query}"
                    )
                    continue
                else:
                    logging.warning(
                        f"Pokemon TCG API HTTP error {e.code} for query: {query}"
                    )
                    continue
            except Exception as e:
                logging.warning(f"Pokemon TCG API error for query '{query}': {e}")
                continue

        # If we get here, no queries succeeded
        logging.info(
            f"No Pokemon cards found for {name} after trying all search methods"
        )
        return []

    except TimeoutError as e:
        logging.warning(f"Pokemon TCG API timeout for {name}: {e}")
        return []
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

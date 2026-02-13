# lists.py
# -*- coding: utf-8 -*-

from .interface import APIResource
from .sprite import get_sprite_url
from .api import get_sprite
from .common import get_species_id_from_url
import logging
import requests


def get_fallback_image(pokedex):
    try:
        if pokedex:
            url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pokedex}.png"

            # Perform a quick request to check if the image URL exists (status code 200)
            response = requests.get(url)
            if response.status_code == 200:
                return url
            else:
                logging.warning(
                    f"Image not found at {url}. Status code: {response.status_code}"
                )
                return "default_image.png"  # Return default image if the request fails
        else:
            raise ValueError("Invalid Pokédex number.")
    except Exception as e:
        logging.error(f"Error generating fallback image URL: {e}")
        return "default_image.png"


def get_official_artwork(name, official_artwork, entry_number):
    # If official artwork is missing, call fallback function
    if official_artwork is None:
        logging.warning(
            f"Official artwork missing for {name}. Generating fallback image."
        )
        official_artwork = get_fallback_image(entry_number)
    else:
        official_artwork

    return official_artwork


def fetch_species_data(pokemon_entry):
    """Fetch the species data for a Pokémon."""
    if "name" in pokemon_entry:
        species_name = pokemon_entry["name"]
    elif "pokemon" in pokemon_entry and "name" in pokemon_entry["pokemon"]:
        species_name = pokemon_entry["pokemon"]["name"]
    else:
        logging.error(f"Could not find 'name' or 'pokemon' in entry: {pokemon_entry}")
        return None
    return species_name


class PokemonList:
    def __init__(self, data):
        self.data = data
        self.pokemon_list = []
        self.pokemon_entries = []
        self.key = None

    def identify_key(self):
        """Identify the key that holds the Pokémon entries."""
        possible_keys = [
            "pokemon",
            "pokemon_species",
            "pokemon_entries",
            "pokemon_encounters",
            "held_by_pokemon",
            "learned_by_pokemon",
            "varieties",
        ]
        self.key = next((k for k in possible_keys if k in self.data), None)
        if not self.key:
            logging.error(f"No valid key found in data: {self.data.keys()}")
            raise ValueError("No valid key found in data for Pokémon list.")
        if self.key == "pokemon_entries":
            self.pokemon_entries = [
                entry["pokemon_species"] for entry in self.data[self.key]
            ]
        else:
            self.pokemon_entries = self.data[self.key]

    def add_pokemon_to_list(self, pokemon_name, pokemon):
        """Add a Pokémon's details to the list."""
        if "sprites" in pokemon:
            try:
                if pokemon.get("id"):
                    # Official artwork upstream is keyed by species (National Dex) id,
                    # not form id. Use species id to avoid 404s for forms/variants.
                    species = pokemon.get("species") or {}
                    species_url = species.get("url") if isinstance(species, dict) else None
                    artwork_id = (
                        get_species_id_from_url(species_url)
                        if species_url
                        else pokemon["id"]
                    )

                    # Try to get the sprite URL (use species id so /artwork/<id> works)
                    official_artwork = get_sprite_url(artwork_id, is_artwork=True)

                    # Ensure sprite is cached in the background (species id → no 404)
                    try:
                        get_sprite(
                            "pokemon", artwork_id, other=True, official_artwork=True
                        )
                    except Exception as e:
                        logging.debug(
                            f"Background sprite caching failed for {pokemon_name} (artwork_id: {artwork_id}): {e}"
                        )
                        # Don't let caching failures affect the URL generation
                        pass
                else:
                    official_artwork = None
            except Exception as e:
                logging.warning(f"Error getting artwork URL for {pokemon_name}: {e}")
                # Fallback to raw GitHub URL if sprite URL generation fails
                if pokemon.get("id"):
                    species = pokemon.get("species") or {}
                    species_url = species.get("url") if isinstance(species, dict) else None
                    artwork_id = (
                        get_species_id_from_url(species_url)
                        if species_url
                        else pokemon["id"]
                    )
                    official_artwork = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{artwork_id}.png"
                else:
                    official_artwork = None

            self.pokemon_list.append(
                {
                    "name": pokemon_name,
                    "official_artwork": official_artwork,
                    "id": pokemon.get("id"),
                    "types": pokemon.get("types", []),
                    "sprites": pokemon.get("sprites", {}),
                }
            )
        else:
            logging.warning(f"No sprites found for Pokémon '{pokemon_name}'")

    def handle_species_data(self, species_name):
        """Handle the species data and recursive Pokémon list creation."""
        try:
            species_data = APIResource.fetch_data("pokemon-species", species_name)
            species_pokemon_list = PokemonList(
                species_data["varieties"]
            ).create_pokemon_list()

            entry_number = species_data.get("pokedex_numbers", [{}])[0].get(
                "entry_number", None
            )
            for pokemon in species_pokemon_list:
                pokemon["entry_number"] = entry_number
                pokemon["official_artwork"] = get_official_artwork(
                    pokemon["name"],
                    pokemon["sprites"]
                    .get("other", {})
                    .get("official-artwork", {})
                    .get("front_default"),
                    entry_number,
                )
            self.pokemon_list.extend(species_pokemon_list)
        except Exception as e:
            logging.error(f"Error fetching species data for {species_name}: {e}")

    def process_pokemon_entry(self, pokemon_entry):
        """Process each Pokémon entry based on the identified key."""
        if self.key == "pokemon_species":
            species_name = fetch_species_data(pokemon_entry)
            if species_name:
                self.handle_species_data(species_name)
        else:
            if isinstance(pokemon_entry, dict):
                pokemon_name = (
                    pokemon_entry["name"]
                    if "name" in pokemon_entry
                    else pokemon_entry.get("pokemon", {}).get("name")
                )
            else:
                logging.warning(
                    f"Warning: Invalid Pokémon entry structure under key '{self.key}': {pokemon_entry}"
                )
                return
            if pokemon_name:
                pokemon = APIResource.fetch_data("pokemon", pokemon_name)
                self.add_pokemon_to_list(pokemon_name, pokemon)

    def create_pokemon_list(self):
        """Main method to create a list of Pokémon."""
        try:
            if isinstance(self.data, list):
                self.pokemon_entries = self.data
            else:
                self.identify_key()

            for pokemon_entry in self.pokemon_entries:
                self.process_pokemon_entry(pokemon_entry)

            self.pokemon_list.sort(key=lambda x: x.get("id", float("inf")))
            return self.pokemon_list
        except ValueError as e:
            logging.error(f"Error fetching Pokémon data under key '{self.key}': {e}")
            return []

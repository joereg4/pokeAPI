import logging

import requests
from .api import get_data, get_sprite
from .common import api_url_build, sprite_url_build
from .loaders import *


def get_chain(data, name):
    # Base evolution (start of the chain)
    base_species = data["chain"]["species"]["name"]

    # Recursive function to find and return the full evolution chain with details
    def traverse_chain(chain):
        current_species = chain["species"]["name"]

        # Extract species ID
        species_id = get_species_id_from_url(chain["species"]["url"])

        evolves_to = chain.get("evolves_to", [])

        evolution_details = {}
        if chain["evolution_details"]:
            details = chain["evolution_details"][0]
            attributes_to_grab = [
                "gender", "held_item", "known_move", "known_move_type",
                "location", "min_level", "min_happiness", "min_beauty",
                "min_affection", "needs_overworld_rain", "party_species",
                "party_type", "relative_physical_stats", "time_of_day",
                "trade_species", "turn_upside_down", "trigger"
            ]
            evolution_details = {attr: details[attr] for attr in attributes_to_grab}

        # Assuming you have a function called 'sprite' that fetches the sprite using species_id
        sprite_data = sprite_url_build("pokemon", species_id, other=True, official_artwork=True)

        current_pokemon_info = {
            "name": current_species,
            "species_id": species_id,  # Incorporating species_id
            "sprite": sprite_data,  # Incorporating sprite data
            **evolution_details  # This unpacks the dictionary items into current_pokemon_info
        }

        if not evolves_to:  # End of chain
            return [current_pokemon_info]
        return [current_pokemon_info] + traverse_chain(evolves_to[0])

    # Extract the species ID from the end of the URL
    def get_species_id_from_url(url):
        return int(url.rstrip('/').split('/')[-1])

    # Main part of your function
    base_species = data["chain"]["species"]["name"]
    if name != base_species:
        while data["chain"]["species"]["name"] != name:
            if not data["chain"]["evolves_to"]:  # Check if the list is empty
                raise ValueError(f"Species '{name}' not found in the evolution chain.")
            data["chain"] = data["chain"]["evolves_to"][0]

    # Once we find the species (or if it's the base), we traverse the chain
    return traverse_chain(data["chain"])





class Pokemon:
    def __init__(self, data):
        self.id = data.get("id")
        self.name = data.get("name")
        self.base_experience = data.get("base_experience")
        self.height = data.get("height")
        self.is_default = data.get("is_default")
        self.order = data.get("order")
        self.weight = data.get("weight")
        self.abilities = [Ability(ability) for ability in data.get("abilities", [])]
        self.forms = data.get("forms", [])
        self.game_indices = data.get("game_indices", [])
        self.held_items = [HeldItem(item) for item in data.get("held_items", [])]
        self.location_area_encounters = data.get("location_area_encounters")
        self.moves = [Move(move) for move in data.get("moves", [])]
        self.species = data.get("species")
        self.sprites = data.get("sprites")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "base_experience": self.base_experience,
            "height": self.height,
            "is_default": self.is_default,
            "order": self.order,
            "weight": self.weight,
            "abilities": [ability.to_dict() for ability in self.abilities],
            "forms": self.forms,
            "game_indices": self.game_indices,
            "held_items": [item.to_dict() for item in self.held_items],
            "location_area_encounters": self.location_area_encounters,
            "moves": [move.to_dict() for move in self.moves],
            "species": self.species,
            "sprites": self.sprites,
        }

    def __str__(self):
        return f"Pokemon {self.id}: {self.name}"







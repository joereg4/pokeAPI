import requests
from .api import get_data, get_sprite
from .common import api_url_build, sprite_url_build
from .loaders import *


def get_chain(data, species_name):
    # Base evolution (start of the chain)
    base_species = data["chain"]["species"]["name"]

    # Recursive function to find and return the full evolution chain
    def traverse_chain(chain):
        current_species = chain["species"]["name"]
        evolves_to = chain.get("evolves_to", [])

        if not evolves_to:  # End of chain
            return [current_species]
        return [current_species] + traverse_chain(evolves_to[0])

    # If the given species is not the base, we start by finding the base
    if species_name != base_species:
        while data["chain"]["species"]["name"] != species_name:
            if not data["chain"]["evolves_to"]:  # Check if the list is empty
                raise ValueError(f"Species '{species_name}' not found in the evolution chain.")
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







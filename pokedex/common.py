# common.py
# -*- coding: utf-8 -*-

import os

BASE_URL = "https://pokeapi.co/api/v2"
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites"
ENDPOINTS = [
    "ability",
    "berry",
    "berry-firmness",
    "berry-flavor",
    "characteristic",
    "contest-effect",
    "contest-type",
    "egg-group",
    "encounter-condition",
    "encounter-condition-value",
    "encounter-method",
    "evolution-chain",
    "evolution-trigger",
    "gender",
    "generation",
    "growth-rate",
    "item",
    "item-attribute",
    "item-category",
    "item-fling-effect",
    "item-pocket",
    "language",
    "location",
    "location-area",
    "machine",
    "move",
    "move-ailment",
    "move-battle-style",
    "move-category",
    "move-damage-class",
    "move-learn-method",
    "move-target",
    "nature",
    "pal-park-area",
    "pokeathlon-stat",
    "pokedex",
    "pokemon",
    "pokemon-color",
    "pokemon-form",
    "pokemon-habitat",
    "pokemon-shape",
    "pokemon-species",
    "region",
    "stat",
    "super-contest-effect",
    "type",
    "version",
    "version-group",
]
SPRITE_EXT = "png"


def get_chain(data, name):
    # logging.info(f"base_species: {base_species}")

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

        sprite_data = sprite_url_build("pokemon", species_id, other=True, official_artwork=True)

        current_pokemon_info = {
            "name": current_species,
            "species_id": species_id,
            "sprite": sprite_data,
            **evolution_details
        }

        evolutions = []
        for evolution in evolves_to:  # Traverse through all possible evolutions
            evolutions.extend(traverse_chain(evolution))

        return [current_pokemon_info] + evolutions

    # Main part of your function
    base_species = data["chain"]["species"]["name"]
    if name != base_species:
        while data["chain"]["species"]["name"] != name:
            if not data["chain"]["evolves_to"]:  # Check if the list is empty
                raise ValueError(f"Species '{name}' not found in the evolution chain.")
            data["chain"] = data["chain"]["evolves_to"][0]

    # Once we find the species (or if it's the base), we traverse the chain
    return traverse_chain(data["chain"])


def get_species_id_from_url(url):
    return int(url.rstrip('/').split('/')[-1])


def validate(endpoint, resource_id=None):
    if endpoint not in ENDPOINTS:
        raise ValueError("Unknown API endpoint '{}'".format(endpoint))

    if resource_id is not None and not isinstance(resource_id, int):
        raise ValueError("Bad id '{}'".format(resource_id))

    return None


def api_url_build(endpoint, resource_id=None, subresource=None):

    validate(endpoint, resource_id)
    if resource_id is not None:
        if subresource is not None:
            return "/".join([BASE_URL, endpoint, str(resource_id), subresource, ""])

        return "/".join([BASE_URL, endpoint, str(resource_id), ""])

    return "/".join([BASE_URL, endpoint, ""])


def cache_uri_build(endpoint, resource_id=None, subresource=None):
    validate(endpoint, resource_id)

    if resource_id is not None:
        if subresource is not None:
            return "/".join([endpoint, str(resource_id), subresource, ""])

        return "/".join([endpoint, str(resource_id), ""])

    return "/".join([endpoint, ""])


def sprite_url_build(sprite_type, sprite_id, **kwargs):
    options = parse_sprite_options(sprite_type, **kwargs)

    filename = ".".join([str(sprite_id), SPRITE_EXT])
    url = "/".join([SPRITE_URL, sprite_type, *options, filename])

    return url


def sprite_filepath_build(sprite_type, sprite_id, **kwargs):
    """returns the filepath of the sprite *relative to SPRITE_CACHE*"""

    options = parse_sprite_options(sprite_type, **kwargs)

    filename = ".".join([str(sprite_id), SPRITE_EXT])
    filepath = os.path.join(sprite_type, *options, filename)

    return filepath


def parse_sprite_options(sprite_type, **kwargs):
    options = []

    if sprite_type == "pokemon":
        if kwargs.get("model", False):
            options.append("model")
        elif kwargs.get("other", False):
            options.append("other")
            if kwargs.get("official_artwork", False):
                options.append("official-artwork")
            if kwargs.get("dream_world", False):
                options.append("dream-world")
        else:
            if kwargs.get("back", False):
                options.append("back")
            if kwargs.get("shiny", False):
                options.append("shiny")
            if kwargs.get("female", False):
                options.append("female")
    elif sprite_type == "items":
        if kwargs.get("berries", False):
            options.append("berries")
        elif kwargs.get("dream_world", False):
            options.append("dream-world")
        elif kwargs.get("gen3", False):
            options.append("gen3")
        elif kwargs.get("gen5", False):
            options.append("gen5")
        elif kwargs.get("underground", False):
            options.append("underground")

    return options





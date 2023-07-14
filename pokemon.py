def get_data(pokemon_name):
    from flask import g

    # Query the MongoDB database for the specified Pokemon
    pokemon = g.db['pokemon'].find_one({"name": pokemon_name})

    if pokemon is not None:
        card_id = pokemon['id']
        card_name = pokemon['name'].title()
        card_image = pokemon['sprites']['other']['official-artwork']['front_default']

        # Process types and moves as before, but get data from MongoDB instead of PokeAPI
        card_type = ', '.join([t['type']['name'] for t in pokemon.get('types', [])])
        card_moves = ', '.join([m['name'] for m in pokemon.get('moves', [])[:20]])

        return card_id, card_name, card_image, card_type, card_moves
    else:
        print('Pokemon not found in the database')
        return None


class Ability:
    def __init__(self, ability):
        if ability is not None:
            self.is_hidden = ability.get("is_hidden")
            self.slot = ability.get("slot")
            self.name = ability.get("ability").get("name")
            self.url = ability.get("ability").get("url")
        else:
            self.is_hidden = None
            self.slot = None
            self.name = None
            self.url = None

    def to_dict(self):
        return {
            "is_hidden": self.is_hidden,
            "slot": self.slot,
            "name": self.name,
            "url": self.url
        }


class HeldItem:
    def __init__(self, item):
        self.name = item.get("item").get("name")
        self.url = item.get("item").get("url")

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url
        }


class Move:
    def __init__(self, move):
        self.name = move.get("move").get("name")
        self.url = move.get("move").get("url")

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url
        }


class Pokemon:
    def __init__(self, data):
        self.id = data.get('id')
        self.name = data.get('name')
        self.base_experience = data.get('base_experience')
        self.height = data.get('height')
        self.is_default = data.get('is_default')
        self.order = data.get('order')
        self.weight = data.get('weight')
        self.abilities = [Ability(ability) for ability in data.get('abilities', [])]
        self.forms = data.get('forms', [])
        self.game_indices = data.get('game_indices', [])
        self.held_items = [HeldItem(item) for item in data.get('held_items', [])]
        self.location_area_encounters = data.get('location_area_encounters')
        self.moves = [Move(move) for move in data.get('moves', [])]
        self.species = data.get('species')
        self.sprites = data.get('sprites')

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
            "sprites": self.sprites
        }

    def __str__(self):
        return f"Pokemon {self.id}: {self.name}"

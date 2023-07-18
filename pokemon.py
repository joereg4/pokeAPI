import requests, json


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

    @staticmethod
    def filter_english_data(data, fields):
        filtered_data = data.copy()
        for field in fields:
            if field in filtered_data:
                entries = filtered_data[field]
                if isinstance(entries, list):
                    filtered_entries = [entry for entry in entries if entry.get('language', {}).get('name') == 'en']
                    filtered_data[field] = filtered_entries
                else:
                    filtered_data[field] = None  # or handle the case when the field is not a list
            else:
                filtered_data[field] = None  # or handle the case when the field doesn't exist
        return filtered_data

    @staticmethod
    def get_evolution_chain(species_id, evolution_chain=None, stage=0):
        if evolution_chain is None:
            evolution_chain = []
        try:
            # Retrieve the species data based on the Pokemon species ID
            response = requests.get(f"https://pokeapi.co/api/v2/pokemon-species/{species_id}")
            response.raise_for_status()
            data = response.json()

            # Filter for English language data if these fields exist
            data = Pokemon.filter_english_data(data, ['names', 'effect_entries', 'flavor_text_entries'])

            # Get the URL for the evolution chain and fetch its data
            evolution_chain_url = data['evolution_chain']['url']
            evolution_chain_response = requests.get(evolution_chain_url)
            evolution_chain_response.raise_for_status()

            chain = evolution_chain_response.json()['chain']

            # A helper function to traverse the chain
            def traverse_chain_link(chain_link, stage):
                species_name = chain_link['species']['name']
                evolves_to = chain_link['evolves_to']

                card_id, card_name, card_image, card_type, card_moves = get_data(species_name)

                # Convert the evolution_stage value to text representation
                if stage == 0:
                    evolution_stage_text = 'Basic Form'
                elif stage == 1 or stage == 2:
                    evolution_stage_text = f'Stage {stage} Evolution'
                elif stage == 3:
                    evolution_stage_text = 'Mega Evolution'
                elif stage == 4:
                    evolution_stage_text = 'Gigantamax Form'
                else:
                    evolution_stage_text = f'Stage {stage}'

                evolution_chain.append(
                    {'species_name': species_name,
                     'image_url': card_image,
                     'evolution_stage': evolution_stage_text
                     })
                # Recursive call for every subsequent evolution
                for evolution in evolves_to:
                    traverse_chain_link(evolution, stage + 1)

            # Start traversal from the first pokemon in the chain
            traverse_chain_link(chain, stage)

        except (KeyError, requests.exceptions.RequestException) as e:
            print(f"Error occurred when accessing key in chain or making the request: {e}")
            raise

        return evolution_chain

    def __str__(self):
        return f"Pokemon {self.id}: {self.name}"

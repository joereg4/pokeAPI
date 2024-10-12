import os
import re

# Define the mapping from old endpoints to new endpoints
endpoint_mapping = {
    'pokemon.get_ability': 'abilities_moves_items.get_ability',
    'pokemon.get_berry': 'berries_contests.get_berry',
    'pokemon.get_region': 'locations_regions.get_region',
    'pokemon.get_evolution_chain': 'evolution_growth.get_evolution_chain',
    'pokemon.get_item': 'abilities_moves_items.get_item',
    'pokemon.get_move': 'abilities_moves_items.get_move',
    'pokemon.get_berry_firmness': 'berries_contests.get_berry_firmness',
    'pokemon.get_egg_group': 'breeding.get_egg_group',
    'pokemon.get_machine': 'abilities_moves_items.get_machine',
    'pokemon.get_gender': 'pokemon.get_gender',
    'pokemon.get_type': 'pokemon.get_type',
    'pokemon.get_version': 'utilities.get_version',
    'pokemon.get_language': 'utilities.get_language',
    'pokemon.get_pokemon_species': 'pokemon.get_pokemon_species',
    'pokemon.get_characteristic': 'characteristics_stats.get_characteristic',
    'pokemon.get_stat': 'characteristics_stats.get_stat',
    'pokemon.get_encounter_condition': 'utilities.get_encounter_condition',
    'pokemon.get_move_category': 'abilities_moves_items.get_move_category',
    'pokemon.get_move_target': 'abilities_moves_items.get_move_target',
    'pokemon.get_location': 'locations_regions.get_location',
    'pokemon.get_location_area': 'locations_regions.get_location_area',
    'pokemon.get_contest_effect': 'berries_contests.get_contest_effect',
    'pokemon.get_contest_type': 'berries_contests.get_contest_type',
    'pokemon.get_berry_flavor': 'berries_contests.get_berry_flavor',
    'pokemon.get_growth_rate': 'evolution_growth.get_growth_rate',
    'pokemon.get_evolution_trigger': 'evolution_growth.get_evolution_trigger',
    'pokemon.get_super_contest_effect': 'berries_contests.get_super_contest_effect'
}

# Directory containing your templates
templates_dir = 'templates'

# Iterate over all files in the templates directory
for root, _, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            file_path = os.path.join(root, file)

            # Read the file content
            with open(file_path, 'r') as f:
                content = f.read()

            # Replace each endpoint based on the mapping
            for old_endpoint, new_endpoint in endpoint_mapping.items():
                content = re.sub(rf"\b{old_endpoint}\b", new_endpoint, content)

            # Write the updated content back to the file
            with open(file_path, 'w') as f:
                f.write(content)

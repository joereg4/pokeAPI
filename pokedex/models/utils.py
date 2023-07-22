import requests

BASE_URL = "https://pokeapi.co/api/v2"

def get_data(pokemon_name):
    from flask import g

    # Query the MongoDB database for the specified Pokemon
    pokemon = g.db["pokemon"].find_one({"name": pokemon_name})

    if pokemon is not None:
        card_id = pokemon["id"]
        card_name = pokemon["name"].title()
        card_image = pokemon["sprites"]["other"]["official-artwork"]["front_default"]

        # Process types and moves as before, but get data from MongoDB instead of PokeAPI
        card_type = ", ".join([t["type"]["name"] for t in pokemon.get("types", [])])
        card_moves = ", ".join([m["name"] for m in pokemon.get("moves", [])[:20]])

        return card_id, card_name, card_image, card_type, card_moves
    else:
        print("Pokemon not found in the database")
        return None


def filter_english_data(data):
    filtered_data = data.copy()
    fields_to_filter = [
        "names",
        "effect_entries",
        "flavor_text_entries",
        "color",
        "genera",
        "habitat",
        "shape",
        "descriptions",
    ]

    for field in fields_to_filter:
        if field in filtered_data:
            entries = filtered_data[field]
            if isinstance(entries, list):
                filtered_entries = [
                    entry
                    for entry in entries
                    if entry.get("language", {}).get("name") == "en"
                ]
                filtered_data[field] = filtered_entries
            else:
                filtered_data[
                    field
                ] = None  # or handle the case when the field is not a list

    return filtered_data


def get_evolution_chain(species_id, evolution_chain=None, stage=0):
    if evolution_chain is None:
        evolution_chain = []
    try:
        # Retrieve the species data based on the Pokemon species ID
        response = requests.get(
            f"{BASE_URL}/pokemon-species/{species_id}"
        )
        response.raise_for_status()
        data = response.json()

        # Filter for English language data if these fields exist
        data = filter_english_data(data)
        print(f"Evelution Data: {data}")
        # Get the URL for the evolution chain and fetch its data
        evolution_chain_url = data["evolution_chain"]["url"]
        evolution_chain_response = requests.get(evolution_chain_url)
        evolution_chain_response.raise_for_status()

        chain = evolution_chain_response.json()["chain"]

        # A helper function to traverse the chain
        def traverse_chain_link(chain_link, stage):
            species_name = chain_link["species"]["name"]
            evolves_to = chain_link["evolves_to"]

            card_id, card_name, card_image, card_type, card_moves = get_data(
                species_name
            )

            # Convert the evolution_stage value to text representation
            if stage == 0:
                evolution_stage_text = "Basic Form"
            elif stage == 1 or stage == 2:
                evolution_stage_text = f"Stage {stage} Evolution"
            elif stage == 3:
                evolution_stage_text = "Mega Evolution"
            elif stage == 4:
                evolution_stage_text = "Gigantamax Form"
            else:
                evolution_stage_text = f"Stage {stage}"

            evolution_chain.append(
                {
                    "species_name": species_name,
                    "image_url": card_image,
                    "evolution_stage": evolution_stage_text,
                }
            )
            # Recursive call for every subsequent evolution
            for evolution in evolves_to:
                traverse_chain_link(evolution, stage + 1)

        # Start traversal from the first pokemon in the chain
        traverse_chain_link(chain, stage)

    except (KeyError, requests.exceptions.RequestException) as e:
        print(f"Error occurred when accessing key in chain or making the request: {e}")
        raise

    return evolution_chain, data

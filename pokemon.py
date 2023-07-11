import urllib.request
import json


class Pokemon:
    def __init__(self, id, name, url, image, type, moves):
        self.id = id
        self.name = name
        self.url = url
        self.image = image
        self.type = type
        self.moves = moves


def get_pokemon_data(pokemon_url):
    request = urllib.request.Request(pokemon_url)
    request.add_header('User-Agent', 'Mozilla 5.10')
    pokemon_data = urllib.request.urlopen(request).read()
    pokemon_json_data = json.loads(pokemon_data)

    pokemons = []

    for pokemon in pokemon_json_data["results"]:
        id, name, url, image, type, moves = get_data(pokemon['url'])
        p = Pokemon(id=id, name=name, url=url, image=image, type=type, moves=moves)
        pokemons.append(p)

    return pokemons, pokemon_json_data.get("next")


def get_data(pokeurl):
    card_url = pokeurl
    card_request = urllib.request.Request(card_url)
    card_request.add_header('User-Agent', 'Mozilla 5.10')
    try:
        card_data = urllib.request.urlopen(card_request).read()
        card_json_data = json.loads(card_data)
        card_id = card_json_data['id']
        card_name = card_json_data['name'].title()
        card_image = card_json_data['sprites']['other']['official-artwork']['front_default']
        type_list = []
        for card_type in card_json_data['types']:
            card_type = {card_type['type']['name']}
            type_list.append(card_type)
        card_type = str(type_list).title().replace("'", "").replace("{", "").replace("}", "").replace("[", "").replace(
            "]", "")
        moves_list = []
        for move in card_json_data['moves']:
            move = {move['move']['name']}
            moves_list.append(move)
        card_moves = str(moves_list).title().replace("'", "").replace("{", "").replace("}", "").replace("[",
                                                                                                        "").replace(
            "]", "")
        return card_id, card_name, pokeurl, card_image, card_type, card_moves
    except:
        print('Something broke')

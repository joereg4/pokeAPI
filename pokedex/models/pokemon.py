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

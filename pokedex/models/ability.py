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
class Move:
    def __init__(self, move):
        self.name = move.get("move").get("name")
        self.url = move.get("move").get("url")

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url
        }
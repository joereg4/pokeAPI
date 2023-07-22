class HeldItem:
    def __init__(self, item):
        self.name = item.get("item").get("name")
        self.url = item.get("item").get("url")

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url
        }
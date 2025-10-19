from dataclasses import dataclass

@dataclass()
class MongoPost:
    reid: str
    title: str
    pages: list[str]
    section: str
    pass

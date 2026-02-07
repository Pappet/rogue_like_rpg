from typing import List
from entities.hero import Hero

class Player:
    def __init__(self, x: int, y: int, sprite: str = "@"):
        self.x = x
        self.y = y
        self.sprite = sprite
        self.party: List[Hero] = []

    def add_hero(self, hero: Hero):
        self.party.append(hero)

    def __repr__(self):
        return f"Player(x={self.x}, y={self.y}, party={self.party})"

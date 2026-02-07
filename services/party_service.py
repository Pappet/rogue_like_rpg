from entities.player import Player
from entities.hero import Hero

class PartyService:
    def __init__(self):
        pass

    def create_initial_party(self, x: int, y: int) -> Player:
        player = Player(x, y)
        player.add_hero(Hero("Hero 1", 10, 10))
        return player

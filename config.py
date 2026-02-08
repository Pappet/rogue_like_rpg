from enum import Enum


# Game configuration
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Rogue Like RPG"
TILE_SIZE = 32


class SpriteLayer(Enum):


    GROUND = 0


    DECOR_BOTTOM = 1


    TRAPS = 2


    ITEMS = 3


    CORPSES = 4


    ENTITIES = 5


    DECOR_TOP = 6


    EFFECTS = 7





class GameStates(Enum):


    PLAYER_TURN = 1


    ENEMY_TURN = 2


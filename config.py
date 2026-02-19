from enum import Enum


# Game configuration
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Rogue Like RPG"
TILE_SIZE = 32

# Debug configuration
DEBUG_FOV_COLOR = (0, 255, 0, 50)
DEBUG_CHASE_COLOR = (255, 165, 0)
DEBUG_LABEL_COLOR = (255, 255, 255)
DEBUG_FONT_SIZE = 12
DEBUG_NPC_FOV_COLOR = (255, 0, 0, 30)
DEBUG_ARROW_COLOR = (255, 255, 0)
DEBUG_TEXT_BG_COLOR = (0, 0, 0, 150)

# UI configuration
HEADER_HEIGHT = 48
SIDEBAR_WIDTH = 160
LOG_HEIGHT = 140

# World Clock configuration
TICKS_PER_HOUR = 60
DAWN_START = 5
DAY_START = 7
DUSK_START = 18
NIGHT_START = 20


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

    TARGETING = 3

    WORLD_MAP = 4

    INVENTORY = 5








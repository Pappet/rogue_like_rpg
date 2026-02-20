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
UI_PADDING = 10
UI_MARGIN = 15
UI_LINE_SPACING = 22
UI_SECTION_SPACING = 35
UI_COLOR_BG_HEADER = (30, 30, 30)
UI_COLOR_BG_SIDEBAR = (40, 40, 40)
UI_COLOR_BORDER = (100, 100, 100)
UI_COLOR_TEXT_DIM = (150, 150, 150)
UI_COLOR_TEXT_BRIGHT = (255, 255, 255)
UI_COLOR_SECTION_TITLE = (200, 200, 200)
UI_BAR_HEIGHT = 18

# World Clock configuration
TICKS_PER_HOUR = 60
DAWN_START = 5
DAY_START = 7
DUSK_START = 18
NIGHT_START = 20

# Day/Night Settings
DN_SETTINGS = {
    "day":   {"tint": (0, 0, 0, 0),     "light": 1.0, "perception": 1.0},
    "dawn":  {"tint": (255, 200, 150, 60), "light": 0.8, "perception": 0.8},
    "dusk":  {"tint": (150, 100, 200, 80), "light": 0.7, "perception": 0.7},
    "night": {"tint": (0, 0, 40, 140),     "light": 0.4, "perception": 0.5},
}


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








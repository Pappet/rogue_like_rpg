# Game configuration
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Rogue Like RPG"
TILE_SIZE = 32

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

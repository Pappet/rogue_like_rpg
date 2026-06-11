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

# Save game
SAVE_FILE = "saves/save.json"

# Off-screen world simulation
# Minimum absence (in ticks) before NPCs are snapped to their scheduled
# positions on arrival — short door hops must not teleport anyone.
SIM_RECONCILE_MIN_TICKS = 30
# Chance per location per in-game hour that a chronicle event happens
SIM_EVENT_CHANCE_PER_HOUR = 0.04

# Settlement economy (ROADMAP Phase C)
ECON_EQUILIBRIUM_STOCK = 5.0  # stock level at which price factor is ~1.0
ECON_MAX_STOCK = 20.0  # stock cap per good per settlement
ECON_PRICE_FACTOR_MIN = 0.5  # abundant goods bottom out at half value
ECON_PRICE_FACTOR_MAX = 2.0  # scarce goods top out at double value

# Day/Night Settings
DN_SETTINGS = {
    "day": {"tint": (0, 0, 0, 0), "light": 1.0, "perception": 1.0},
    "dawn": {"tint": (255, 200, 150, 60), "light": 0.8, "perception": 0.8},
    "dusk": {"tint": (150, 100, 200, 80), "light": 0.7, "perception": 0.7},
    "night": {"tint": (0, 0, 40, 140), "light": 0.4, "perception": 0.5},
}

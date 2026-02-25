from enum import Enum
from config.colors import COLOR_GOLD, COLOR_YELLOW


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

    MENU = 6

    EXAMINE = 7

    GAME_OVER = 8


class LogCategory(Enum):
    DAMAGE_DEALT = 1
    DAMAGE_RECEIVED = 2
    HEALING = 3
    LOOT = 4
    SYSTEM = 5
    ALERT = 6


LOG_COLORS = {
    LogCategory.DAMAGE_DEALT: (100, 255, 100),    # Light Green
    LogCategory.DAMAGE_RECEIVED: (255, 100, 100), # Light Red
    LogCategory.HEALING: (50, 200, 255),          # Light Blue
    LogCategory.LOOT: COLOR_GOLD,                 # Gold
    LogCategory.SYSTEM: (200, 200, 200),          # Light Gray
    LogCategory.ALERT: COLOR_YELLOW,              # Yellow
}

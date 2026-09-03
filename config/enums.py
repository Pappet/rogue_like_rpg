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


class GameEvent(str, Enum):
    """Every esper event name in the game, in one place.

    Event names used to be bare string literals at both ends of the wire; a
    typo in a handler is a silent no-op, because nothing connects a
    ``dispatch_event`` to its ``set_handler``. These members are the only
    sanctioned spelling — ``tests/verify_events.py`` fails the build if a bare
    literal creeps back in.

    Deriving from ``str`` keeps them drop-in compatible with esper's
    string-keyed registry (and with tests that still pass plain strings).

    Facts (past tense) are reported to whoever cares; ``*_requested`` events
    are the sanctioned way for a lower layer to ask the orchestration layer
    for something it must not call directly. See the Event Policy in
    CLAUDE.md.
    """

    # --- Facts ---------------------------------------------------------------
    LOG_MESSAGE = "log_message"
    ENTITY_DIED = "entity_died"
    PLAYER_DIED = "player_died"
    CLOCK_TICK = "clock_tick"
    SKILL_INCREASED = "skill_increased"

    # --- Requests ------------------------------------------------------------
    MAP_CHANGE_REQUESTED = "map_change_requested"
    DIALOGUE_REQUESTED = "dialogue_requested"
    TRADE_REQUESTED = "trade_requested"
    QUESTS_REQUESTED = "quests_requested"
    REST_REQUESTED = "rest_requested"
    CRAFT_REQUESTED = "craft_requested"
    HARVEST_REQUESTED = "harvest_requested"
    PICKUP_CHOICE_REQUESTED = "pickup_choice_requested"


LOG_COLORS = {
    LogCategory.DAMAGE_DEALT: (100, 255, 100),  # Light Green
    LogCategory.DAMAGE_RECEIVED: (255, 100, 100),  # Light Red
    LogCategory.HEALING: (50, 200, 255),  # Light Blue
    LogCategory.LOOT: COLOR_GOLD,  # Gold
    LogCategory.SYSTEM: (200, 200, 200),  # Light Gray
    LogCategory.ALERT: COLOR_YELLOW,  # Yellow
}

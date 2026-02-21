import pygame
from enum import Enum, auto
from config import GameStates

class InputCommand(Enum):
    # Movement
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    
    # Interactions
    INTERACT = auto() # G
    CONFIRM = auto() # RETURN
    CANCEL = auto() # ESCAPE
    
    # UI / Menus
    OPEN_INVENTORY = auto() # I
    OPEN_WORLD_MAP = auto() # M
    NEXT_ACTION = auto() # S
    PREVIOUS_ACTION = auto() # W
    NEXT_TARGET = auto() # TAB
    
    # Hotbar
    HOTBAR_1 = auto()
    HOTBAR_2 = auto()
    HOTBAR_3 = auto()
    HOTBAR_4 = auto()
    HOTBAR_5 = auto()
    HOTBAR_6 = auto()
    HOTBAR_7 = auto()
    HOTBAR_8 = auto()
    HOTBAR_9 = auto()
    
    # Inventory Actions
    DROP_ITEM = auto() # D
    USE_ITEM = auto() # U
    EQUIP_ITEM = auto() # E
    
    # Debug
    DEBUG_TOGGLE_MASTER = auto()
    DEBUG_TOGGLE_PLAYER_FOV = auto()
    DEBUG_TOGGLE_NPC_FOV = auto()
    DEBUG_TOGGLE_CHASE = auto()
    DEBUG_TOGGLE_LABELS = auto()

class InputManager:
    def __init__(self):
        # Context-aware mappings
        self._maps = {
            GameStates.PLAYER_TURN: {
                pygame.K_UP: InputCommand.MOVE_UP,
                pygame.K_DOWN: InputCommand.MOVE_DOWN,
                pygame.K_LEFT: InputCommand.MOVE_LEFT,
                pygame.K_RIGHT: InputCommand.MOVE_RIGHT,
                pygame.K_w: InputCommand.PREVIOUS_ACTION,
                pygame.K_s: InputCommand.NEXT_ACTION,
                pygame.K_g: InputCommand.INTERACT,
                pygame.K_i: InputCommand.OPEN_INVENTORY,
                pygame.K_m: InputCommand.OPEN_WORLD_MAP,
                pygame.K_RETURN: InputCommand.CONFIRM,
                pygame.K_F3: InputCommand.DEBUG_TOGGLE_MASTER,
                pygame.K_F4: InputCommand.DEBUG_TOGGLE_PLAYER_FOV,
                pygame.K_F5: InputCommand.DEBUG_TOGGLE_NPC_FOV,
                pygame.K_F6: InputCommand.DEBUG_TOGGLE_CHASE,
                pygame.K_F7: InputCommand.DEBUG_TOGGLE_LABELS,
                pygame.K_1: InputCommand.HOTBAR_1,
                pygame.K_2: InputCommand.HOTBAR_2,
                pygame.K_3: InputCommand.HOTBAR_3,
                pygame.K_4: InputCommand.HOTBAR_4,
                pygame.K_5: InputCommand.HOTBAR_5,
                pygame.K_6: InputCommand.HOTBAR_6,
                pygame.K_7: InputCommand.HOTBAR_7,
                pygame.K_8: InputCommand.HOTBAR_8,
                pygame.K_9: InputCommand.HOTBAR_9,
            },
            GameStates.TARGETING: {
                pygame.K_UP: InputCommand.MOVE_UP,
                pygame.K_w: InputCommand.MOVE_UP,
                pygame.K_DOWN: InputCommand.MOVE_DOWN,
                pygame.K_s: InputCommand.MOVE_DOWN,
                pygame.K_LEFT: InputCommand.MOVE_LEFT,
                pygame.K_a: InputCommand.MOVE_LEFT,
                pygame.K_RIGHT: InputCommand.MOVE_RIGHT,
                pygame.K_d: InputCommand.MOVE_RIGHT,
                pygame.K_RETURN: InputCommand.CONFIRM,
                pygame.K_ESCAPE: InputCommand.CANCEL,
                pygame.K_TAB: InputCommand.NEXT_TARGET,
            },
            GameStates.INVENTORY: {
                pygame.K_UP: InputCommand.MOVE_UP,
                pygame.K_w: InputCommand.MOVE_UP,
                pygame.K_DOWN: InputCommand.MOVE_DOWN,
                pygame.K_s: InputCommand.MOVE_DOWN,
                pygame.K_ESCAPE: InputCommand.CANCEL,
                pygame.K_i: InputCommand.CANCEL,
                pygame.K_d: InputCommand.DROP_ITEM,
                pygame.K_u: InputCommand.USE_ITEM,
                pygame.K_e: InputCommand.EQUIP_ITEM,
                pygame.K_RETURN: InputCommand.CONFIRM,
            },
            GameStates.WORLD_MAP: {
                pygame.K_ESCAPE: InputCommand.CANCEL,
                pygame.K_m: InputCommand.CANCEL,
            }
        }
        
        # Default map for any other state
        self._default_map = {
            pygame.K_ESCAPE: InputCommand.CANCEL,
            pygame.K_RETURN: InputCommand.CONFIRM,
        }

    def handle_event(self, event, state=None):
        """
        Translates a pygame event into an InputCommand based on the current state.
        Returns InputCommand or None if no mapping exists for the key.
        """
        if event.type != pygame.KEYDOWN:
            return None
            
        mapping = self._maps.get(state, self._default_map)
        return mapping.get(event.key)

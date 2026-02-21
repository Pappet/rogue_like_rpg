import pygame
import sys
import os

# Mock pygame to avoid window creation
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()

from services.input_manager import InputManager, InputCommand
from config import GameStates

def test_input_manager():
    im = InputManager()
    
    # Test PLAYER_TURN UP
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)
    cmd = im.handle_event(event, GameStates.PLAYER_TURN)
    assert cmd == InputCommand.MOVE_UP
    print("Test PLAYER_TURN UP: PASSED")
    
    # Test TARGETING ESCAPE
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    cmd = im.handle_event(event, GameStates.TARGETING)
    assert cmd == InputCommand.CANCEL
    print("Test TARGETING ESCAPE: PASSED")
    
    # Test INVENTORY D
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
    cmd = im.handle_event(event, GameStates.INVENTORY)
    assert cmd == InputCommand.DROP_ITEM
    print("Test INVENTORY D: PASSED")

    # Test INVENTORY W (WASD support)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w)
    cmd = im.handle_event(event, GameStates.INVENTORY)
    assert cmd == InputCommand.MOVE_UP
    print("Test INVENTORY W: PASSED")
    
    # Test TARGETING A
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
    cmd = im.handle_event(event, GameStates.TARGETING)
    assert cmd == InputCommand.MOVE_LEFT
    print("Test TARGETING A: PASSED")

    # Test unknown key
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p)
    cmd = im.handle_event(event, GameStates.PLAYER_TURN)
    assert cmd is None
    print("Test unknown key: PASSED")

if __name__ == "__main__":
    try:
        test_input_manager()
        print("All InputManager tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)

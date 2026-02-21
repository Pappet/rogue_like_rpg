import sys
import os

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import esper
from services.party_service import PartyService
from ecs.components import HotbarSlots, Action
from services.input_manager import InputManager, InputCommand, GameStates

def test_hotbar_infrastructure():
    esper.clear_database()
    party_service = PartyService()
    player = party_service.create_initial_party(1, 1)
    
    assert esper.has_component(player, HotbarSlots)
    hotbar = esper.component_for_entity(player, HotbarSlots)
    
    # Check if slot 1 has "Move" action
    assert hotbar.slots[1].name == "Move"
    # Check if slot 2 has "Wait" action
    assert hotbar.slots[2].name == "Wait"
    
    print("Hotbar Infrastructure test passed!")

def test_hotbar_input_mapping():
    input_manager = InputManager()
    
    import pygame
    event_1 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
    command_1 = input_manager.handle_event(event_1, GameStates.PLAYER_TURN)
    assert command_1 == InputCommand.HOTBAR_1
    
    event_9 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_9)
    command_9 = input_manager.handle_event(event_9, GameStates.PLAYER_TURN)
    assert command_9 == InputCommand.HOTBAR_9
    
    print("Hotbar Input Mapping test passed!")

if __name__ == "__main__":
    # Initialize pygame for events (or just mock it if needed, but pygame.event.Event works without init)
    test_hotbar_infrastructure()
    test_hotbar_input_mapping()

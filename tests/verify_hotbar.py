import os
import sys

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import esper

from core.input_manager import GameStates, InputCommand, InputManager
from game.services.party_service import PartyService


def test_no_hotbar_infrastructure():
    esper.clear_database()
    party_service = PartyService()
    player = party_service.create_initial_party(1, 1)

    import game.components

    has_hotbar_component = hasattr(game.components, "HotbarSlots")
    assert not has_hotbar_component, "HotbarSlots component should be removed from codebase"

    # Ensure ActionList still exists
    assert esper.has_component(player, game.components.ActionList)
    print("No Hotbar Infrastructure test passed!")


def test_wait_input_mapping():
    input_manager = InputManager()

    import pygame

    event_space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    command_space = input_manager.handle_event(event_space, GameStates.PLAYER_TURN)
    assert command_space == InputCommand.WAIT

    print("Wait Input Mapping test passed!")


if __name__ == "__main__":
    test_no_hotbar_infrastructure()
    test_wait_input_mapping()

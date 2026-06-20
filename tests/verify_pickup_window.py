"""Behaviour tests for the multi-item pickup chooser window.

The window only translates key presses into PlayerActionService calls; the
pickup rules themselves are covered in verify_player_action_service. Here we
assert the wiring: navigation, single take, take-all and close.
"""

from unittest.mock import MagicMock

import esper
import pygame
import pytest

from core.input_manager import InputManager
from game.components import Inventory, Name, Portable, Position, Stats
from game.services.player_action_service import PlayerActionService
from game.ui.windows.pickup import PickupWindow
from game_context import GameContext, Systems


def _make_ctx(player_entity):
    systems = Systems(
        turn_system=MagicMock(),
        equipment_system=MagicMock(),
        visibility_system=MagicMock(),
        action_system=MagicMock(),
        movement_system=MagicMock(),
        combat_system=MagicMock(),
        fct_system=MagicMock(),
        death_system=MagicMock(),
        ai_system=MagicMock(),
        schedule_system=MagicMock(),
    )
    return GameContext(
        map_service=MagicMock(),
        render_service=MagicMock(),
        world_clock=MagicMock(),
        input_manager=MagicMock(),
        ui_stack=MagicMock(),
        camera=MagicMock(),
        systems=systems,
        player_entity=player_entity,
    )


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


@pytest.fixture
def setup():
    player = esper.create_entity(
        Position(3, 3, 0),
        Inventory(),
        Stats(hp=10, max_hp=10, power=1, defense=0, mana=0, max_mana=0, perception=5, intelligence=5),
    )
    actions = PlayerActionService(_make_ctx(player))
    a = esper.create_entity(Position(3, 3, 0), Portable(weight=1.0), Name("Dagger"))
    b = esper.create_entity(Position(3, 3, 0), Portable(weight=1.0), Name("Apple"))
    window = PickupWindow(pygame.Rect(0, 0, 400, 300), [a, b], actions, InputManager())
    return player, actions, a, b, window


def test_enter_takes_selected_item_and_closes(setup):
    player, actions, a, b, window = setup

    window.handle_event(_key(pygame.K_RETURN))

    inventory = esper.component_for_entity(player, Inventory)
    assert a in inventory.items and b not in inventory.items
    assert window.wants_to_close is True
    actions.ctx.systems.turn_system.end_player_turn.assert_called_once()


def test_navigation_changes_selection(setup):
    player, actions, a, b, window = setup

    window.handle_event(_key(pygame.K_DOWN))
    assert window.selected_idx == 1

    window.handle_event(_key(pygame.K_RETURN))
    inventory = esper.component_for_entity(player, Inventory)
    assert b in inventory.items and a not in inventory.items


def test_a_takes_all_in_one_turn(setup):
    player, actions, a, b, window = setup

    window.handle_event(_key(pygame.K_a))

    inventory = esper.component_for_entity(player, Inventory)
    assert a in inventory.items and b in inventory.items
    assert window.wants_to_close is True
    actions.ctx.systems.turn_system.end_player_turn.assert_called_once()


def test_escape_closes_without_taking(setup):
    player, actions, a, b, window = setup

    window.handle_event(_key(pygame.K_ESCAPE))

    inventory = esper.component_for_entity(player, Inventory)
    assert not inventory.items
    assert window.wants_to_close is True
    actions.ctx.systems.turn_system.end_player_turn.assert_not_called()

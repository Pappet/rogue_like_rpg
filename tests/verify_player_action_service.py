"""Unit tests for PlayerActionService.

These run against the real esper world but mock all systems — no map,
no Pygame, no registries needed.
"""

from unittest.mock import MagicMock

import esper
import pytest

from game.components import (
    Action,
    ActionList,
    Inventory,
    MovementRequest,
    Name,
    Portable,
    Position,
    Stats,
)
from game.services.player_action_service import PlayerActionService
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


def _make_player(**stat_overrides):
    stats = Stats(
        hp=10, max_hp=10, power=1, defense=0, mana=0, max_mana=0, perception=5, intelligence=5, **stat_overrides
    )
    return esper.create_entity(Position(3, 3, 0), Inventory(), stats)


@pytest.fixture
def player():
    return _make_player()


@pytest.fixture
def service(player):
    return PlayerActionService(_make_ctx(player))


def test_move_adds_request_and_ends_turn(service, player):
    service.move(1, 0)

    request = esper.component_for_entity(player, MovementRequest)
    assert (request.dx, request.dy) == (1, 0)
    service.ctx.systems.turn_system.end_player_turn.assert_called_once()


def test_pickup_moves_item_to_inventory_and_ends_turn(service, player):
    item = esper.create_entity(Position(3, 3, 0), Portable(weight=1.0), Name("Dagger"))

    assert service.pickup_item() is True

    inventory = esper.component_for_entity(player, Inventory)
    assert item in inventory.items
    assert not esper.has_component(item, Position)
    service.ctx.systems.turn_system.end_player_turn.assert_called_once()


def test_pickup_rejects_overweight_item(service, player):
    item = esper.create_entity(Position(3, 3, 0), Portable(weight=999.0), Name("Anvil"))

    assert service.pickup_item() is False

    inventory = esper.component_for_entity(player, Inventory)
    assert item not in inventory.items
    assert esper.has_component(item, Position)
    service.ctx.systems.turn_system.end_player_turn.assert_not_called()


def test_pickup_with_nothing_here_does_not_end_turn(service):
    assert service.pickup_item() is False
    service.ctx.systems.turn_system.end_player_turn.assert_not_called()


def test_pickup_ignores_items_on_other_tiles(service, player):
    esper.create_entity(Position(4, 3, 0), Portable(weight=1.0), Name("Far Dagger"))

    assert service.pickup_item() is False


def test_pickup_with_multiple_items_opens_chooser(service, player):
    """A tile with >1 item dispatches the chooser event instead of grabbing
    a random one, and does not consume the turn yet."""
    a = esper.create_entity(Position(3, 3, 0), Portable(weight=1.0), Name("Dagger"))
    b = esper.create_entity(Position(3, 3, 0), Portable(weight=1.0), Name("Apple"))

    captured = []

    def on_choice(items):
        captured.append(items)

    esper.set_handler("pickup_choice_requested", on_choice)

    assert service.pickup_item() is False
    assert captured and set(captured[0]) == {a, b}
    # Nothing taken, no turn spent — the window will drive the actual pickup.
    inventory = esper.component_for_entity(player, Inventory)
    assert a not in inventory.items and b not in inventory.items
    service.ctx.systems.turn_system.end_player_turn.assert_not_called()


def test_items_at_player_lists_only_local_items(service, player):
    here = esper.create_entity(Position(3, 3, 0), Portable(weight=1.0), Name("Here"))
    esper.create_entity(Position(4, 3, 0), Portable(weight=1.0), Name("There"))

    assert service.items_at_player() == [here]


def test_pickup_specific_can_skip_ending_turn(service, player):
    item = esper.create_entity(Position(3, 3, 0), Portable(weight=1.0), Name("Dagger"))

    assert service.pickup_specific(item, end_turn=False) is True

    inventory = esper.component_for_entity(player, Inventory)
    assert item in inventory.items
    service.ctx.systems.turn_system.end_player_turn.assert_not_called()


def test_pickup_all_takes_everything_that_fits_in_one_turn(service, player):
    a = esper.create_entity(Position(3, 3, 0), Portable(weight=1.0), Name("Dagger"))
    b = esper.create_entity(Position(3, 3, 0), Portable(weight=1.0), Name("Apple"))

    assert service.pickup_all([a, b]) is True

    inventory = esper.component_for_entity(player, Inventory)
    assert a in inventory.items and b in inventory.items
    # Several items, but only a single turn is spent.
    service.ctx.systems.turn_system.end_player_turn.assert_called_once()


def test_try_enter_portal_without_portal_returns_false(service):
    assert service.try_enter_portal() is False
    service.ctx.systems.action_system.perform_action.assert_not_called()


def test_try_enter_portal_with_portal_performs_action(service, player):
    from game.components import Portal

    esper.create_entity(Position(3, 3, 0), Portal(target_map_id="X", target_x=0, target_y=0, target_layer=0))
    service.ctx.systems.action_system.perform_action.return_value = True

    assert service.try_enter_portal() is True
    ent, action = service.ctx.systems.action_system.perform_action.call_args[0]
    assert ent == player
    assert action.name == "Enter Portal"


def test_wait_ends_turn(service, player):
    service.wait()
    service.ctx.systems.turn_system.end_player_turn.assert_called_once()


def test_select_action_wraps_around(service, player):
    actions = [Action("Move"), Action("Attack"), Action("Items")]
    esper.add_component(player, ActionList(actions=actions, selected_idx=0))

    service.select_action(-1)
    assert esper.component_for_entity(player, ActionList).selected_idx == 2
    service.select_action(1)
    assert esper.component_for_entity(player, ActionList).selected_idx == 0


def test_confirm_selected_action_skips_move(service, player):
    esper.add_component(player, ActionList(actions=[Action("Move")], selected_idx=0))

    service.confirm_selected_action()

    service.ctx.systems.action_system.perform_action.assert_not_called()
    service.ctx.systems.action_system.start_targeting.assert_not_called()


def test_start_and_stop_examine_toggle_turn_state(service, player):
    from config import GameStates

    service.ctx.systems.action_system.start_targeting.return_value = True
    assert service.start_examine() is True
    assert service.ctx.systems.turn_system.current_state == GameStates.EXAMINE

    service.stop_examine()
    assert service.ctx.systems.turn_system.current_state == GameStates.PLAYER_TURN
    service.ctx.systems.action_system.cancel_targeting.assert_called_once_with(player)

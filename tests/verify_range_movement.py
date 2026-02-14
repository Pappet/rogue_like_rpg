"""Verification tests for Phase 13 range and movement rules.

Tests that:
1. Inspect targeting range equals the player's perception stat (INV-02).
2. Combat targeting range is NOT affected by perception stat (regression guard).
3. Cursor moves successfully onto a SHROUDED tile.
4. Cursor moves successfully onto a FORGOTTEN tile.
5. Cursor is blocked when the target tile is UNEXPLORED (TILE-03).
6. Cursor is blocked when the move exceeds the perception-derived range.
7. Sanity: Investigate action starts targeting successfully (Phase 12 regression guard).

Run from project root:
    python -m pytest tests/verify_range_movement.py -v
"""

import sys
import os

# Ensure project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import esper

from ecs.world import get_world, reset_world
from ecs.components import (
    Position, Stats, ActionList, Action, Targeting
)
from ecs.systems.action_system import ActionSystem
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile, VisibilityState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_stats(perception: int = 10, hp: int = 100, max_hp: int = 100) -> Stats:
    return Stats(
        hp=hp, max_hp=max_hp, power=5, defense=2,
        mana=50, max_mana=50, perception=perception, intelligence=10
    )


def make_map_with_visibility(width: int, height: int, visibility_map) -> MapContainer:
    """Build a MapContainer where each tile's visibility_state matches visibility_map.

    Args:
        width: number of columns.
        height: number of rows.
        visibility_map: 2D list (row-major) of VisibilityState values, or a single
                        VisibilityState to use for every tile.
    """
    if isinstance(visibility_map, VisibilityState):
        # Uniform map shortcut.
        uniform = visibility_map
        visibility_map = [[uniform] * width for _ in range(height)]

    tiles = [[Tile() for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            tiles[y][x].visibility_state = visibility_map[y][x]

    layer = MapLayer(tiles)
    return MapContainer([layer])


class MockTurnSystem:
    """Minimal TurnSystem replacement."""
    def __init__(self):
        from config import GameStates
        self.current_state = GameStates.PLAYER_TURN
        self.end_turn_called = False

    def end_player_turn(self):
        self.end_turn_called = True

    def end_enemy_turn(self):
        pass


# ---------------------------------------------------------------------------
# Test 1: Inspect targeting range equals perception stat (INV-02)
# ---------------------------------------------------------------------------

def test_inspect_targeting_range_equals_perception():
    """start_targeting() for inspect mode must set range to stats.perception."""
    reset_world()

    map_container = make_map_with_visibility(12, 12, VisibilityState.VISIBLE)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(5, 5),
        make_stats(perception=3),
    )

    action_system = ActionSystem(map_container, turn_system)

    # Investigate action with static range=10 — perception should override it.
    investigate = Action(
        name="Investigate", range=10, requires_targeting=True, targeting_mode="inspect"
    )
    started = action_system.start_targeting(player, investigate)
    assert started, "start_targeting() returned False — targeting did not begin"

    targeting = esper.component_for_entity(player, Targeting)
    assert targeting.range == 3, (
        f"Expected targeting.range == 3 (perception), got {targeting.range}"
    )


# ---------------------------------------------------------------------------
# Test 2: Combat targeting range is unchanged by perception (regression)
# ---------------------------------------------------------------------------

def test_combat_targeting_range_unchanged():
    """start_targeting() for auto/combat mode must NOT change range to perception."""
    reset_world()

    map_container = make_map_with_visibility(5, 5, VisibilityState.VISIBLE)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(perception=3),
    )

    action_system = ActionSystem(map_container, turn_system)

    combat_action = Action(
        name="Ranged", range=5, requires_targeting=True, targeting_mode="auto"
    )
    started = action_system.start_targeting(player, combat_action)
    assert started, "start_targeting() returned False — targeting did not begin"

    targeting = esper.component_for_entity(player, Targeting)
    assert targeting.range == 5, (
        f"Expected targeting.range == 5 (combat range unchanged), got {targeting.range}"
    )


# ---------------------------------------------------------------------------
# Test 3: Cursor moves successfully onto a SHROUDED tile
# ---------------------------------------------------------------------------

def test_cursor_moves_to_shrouded_tile():
    """move_cursor() must allow movement onto SHROUDED tiles."""
    reset_world()

    # 5x5 map: all VISIBLE except (3,2) which is SHROUDED.
    vis = [[VisibilityState.VISIBLE] * 5 for _ in range(5)]
    vis[2][3] = VisibilityState.SHROUDED
    map_container = make_map_with_visibility(5, 5, vis)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(perception=10),
    )

    action_system = ActionSystem(map_container, turn_system)

    investigate = Action(
        name="Investigate", range=10, requires_targeting=True, targeting_mode="inspect"
    )
    action_system.start_targeting(player, investigate)

    # Move cursor right (dx=1, dy=0) — should land on (3,2).
    action_system.move_cursor(player, 1, 0)

    targeting = esper.component_for_entity(player, Targeting)
    assert targeting.target_x == 3, (
        f"Expected cursor at x=3, got {targeting.target_x}"
    )
    assert targeting.target_y == 2, (
        f"Expected cursor at y=2, got {targeting.target_y}"
    )


# ---------------------------------------------------------------------------
# Test 4: Cursor moves successfully onto a FORGOTTEN tile
# ---------------------------------------------------------------------------

def test_cursor_moves_to_forgotten_tile():
    """move_cursor() must allow movement onto FORGOTTEN tiles."""
    reset_world()

    # 5x5 map: all VISIBLE except (3,2) which is FORGOTTEN.
    vis = [[VisibilityState.VISIBLE] * 5 for _ in range(5)]
    vis[2][3] = VisibilityState.FORGOTTEN
    map_container = make_map_with_visibility(5, 5, vis)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(perception=10),
    )

    action_system = ActionSystem(map_container, turn_system)

    investigate = Action(
        name="Investigate", range=10, requires_targeting=True, targeting_mode="inspect"
    )
    action_system.start_targeting(player, investigate)

    # Move cursor right (dx=1, dy=0) — should land on (3,2).
    action_system.move_cursor(player, 1, 0)

    targeting = esper.component_for_entity(player, Targeting)
    assert targeting.target_x == 3, (
        f"Expected cursor at x=3, got {targeting.target_x}"
    )
    assert targeting.target_y == 2, (
        f"Expected cursor at y=2, got {targeting.target_y}"
    )


# ---------------------------------------------------------------------------
# Test 5: Cursor blocked on UNEXPLORED tile (TILE-03)
# ---------------------------------------------------------------------------

def test_cursor_blocked_on_unexplored_tile():
    """move_cursor() must NOT move the cursor onto UNEXPLORED tiles."""
    reset_world()

    # 5x5 map: all VISIBLE except (3,2) which is UNEXPLORED.
    vis = [[VisibilityState.VISIBLE] * 5 for _ in range(5)]
    vis[2][3] = VisibilityState.UNEXPLORED
    map_container = make_map_with_visibility(5, 5, vis)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(perception=10),
    )

    action_system = ActionSystem(map_container, turn_system)

    investigate = Action(
        name="Investigate", range=10, requires_targeting=True, targeting_mode="inspect"
    )
    action_system.start_targeting(player, investigate)

    # Attempt to move cursor right — target tile is UNEXPLORED, must be blocked.
    action_system.move_cursor(player, 1, 0)

    targeting = esper.component_for_entity(player, Targeting)
    assert targeting.target_x == 2, (
        f"Expected cursor to stay at x=2 (blocked by UNEXPLORED), got {targeting.target_x}"
    )
    assert targeting.target_y == 2, (
        f"Expected cursor to stay at y=2 (blocked by UNEXPLORED), got {targeting.target_y}"
    )


# ---------------------------------------------------------------------------
# Test 6: Cursor blocked beyond perception range
# ---------------------------------------------------------------------------

def test_cursor_blocked_beyond_perception_range():
    """move_cursor() must not move the cursor beyond the perception-derived range."""
    reset_world()

    # 8x8 all-VISIBLE map. Player at (2,2) with perception=2.
    map_container = make_map_with_visibility(8, 8, VisibilityState.VISIBLE)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(perception=2),
    )

    action_system = ActionSystem(map_container, turn_system)

    investigate = Action(
        name="Investigate", range=10, requires_targeting=True, targeting_mode="inspect"
    )
    action_system.start_targeting(player, investigate)

    # Move 1: (2,2) -> (3,2). dist=1, within range 2. Should succeed.
    action_system.move_cursor(player, 1, 0)
    targeting = esper.component_for_entity(player, Targeting)
    assert targeting.target_x == 3, (
        f"After move 1, expected cursor at x=3, got {targeting.target_x}"
    )

    # Move 2: (3,2) -> (4,2). dist=2 from origin (2,2). Still within range. Should succeed.
    action_system.move_cursor(player, 1, 0)
    targeting = esper.component_for_entity(player, Targeting)
    assert targeting.target_x == 4, (
        f"After move 2, expected cursor at x=4, got {targeting.target_x}"
    )

    # Move 3: (4,2) -> (5,2). dist=3, exceeds range 2. Must be blocked.
    action_system.move_cursor(player, 1, 0)
    targeting = esper.component_for_entity(player, Targeting)
    assert targeting.target_x == 4, (
        f"After move 3, expected cursor still at x=4 (range blocked), got {targeting.target_x}"
    )


# ---------------------------------------------------------------------------
# Test 7: Investigate action starts targeting (Phase 12 sanity regression)
# ---------------------------------------------------------------------------

def test_existing_phase12_tests_unbroken():
    """Lightweight sanity guard: Investigate action must start targeting successfully."""
    reset_world()

    from services.party_service import PartyService
    from ecs.components import ActionList

    map_container = make_map_with_visibility(5, 5, VisibilityState.VISIBLE)
    turn_system = MockTurnSystem()

    party = PartyService()
    player = party.create_initial_party(2, 2)

    action_list = esper.component_for_entity(player, ActionList)
    investigate = next(
        (a for a in action_list.actions if a.name == "Investigate"), None
    )
    assert investigate is not None, "Investigate action not found in ActionList"

    action_system = ActionSystem(map_container, turn_system)
    started = action_system.start_targeting(player, investigate)
    assert started is True, (
        f"start_targeting() returned {started} for Investigate — should return True"
    )

    targeting = esper.component_for_entity(player, Targeting)
    assert targeting is not None, "Targeting component not added to player entity"

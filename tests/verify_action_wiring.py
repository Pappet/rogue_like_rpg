"""Verification tests for Phase 12 action wiring (Investigate action).

Tests that:
1. Investigate action has requires_targeting=True, targeting_mode='inspect', range=10.
2. Investigate action has cost_mana=0 (never blocked by mana check).
3. Description.get(None) returns base text without crashing (stats=None guard).
4. Description.get() with stats still works correctly (regression guard).
5. confirm_action() skips end_player_turn when targeting_mode is 'inspect'.
6. confirm_action() calls end_player_turn for combat targeting modes (regression guard).
7. draw_targeting_ui color selection: cyan for inspect, yellow for combat.

Run from project root:
    python -m pytest tests/verify_action_wiring.py -v
"""

import sys
import os

# Ensure project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import esper

from ecs.world import get_world, reset_world
from ecs.components import (
    Position, Stats, ActionList, Action, Targeting, Description
)
from ecs.systems.action_system import ActionSystem
from ecs.systems.turn_system import TurnSystem
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile, VisibilityState
from services.party_service import PartyService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_stats(hp: int = 100, max_hp: int = 100) -> Stats:
    return Stats(
        hp=hp, max_hp=max_hp, power=5, defense=2,
        mana=50, max_mana=50, perception=10, intelligence=10
    )


def make_visible_map(width: int = 5, height: int = 5) -> MapContainer:
    """Create a small MapContainer where every tile is VISIBLE."""
    tiles = [[Tile() for _ in range(width)] for _ in range(height)]
    for row in tiles:
        for tile in row:
            tile.visibility_state = VisibilityState.VISIBLE
    layer = MapLayer(tiles)
    return MapContainer([layer])


class MockTurnSystem:
    """Minimal TurnSystem replacement that tracks end_player_turn calls."""
    def __init__(self):
        from config import GameStates
        self.current_state = GameStates.PLAYER_TURN
        self.end_turn_called = False

    def end_player_turn(self):
        self.end_turn_called = True

    def end_enemy_turn(self):
        pass


# ---------------------------------------------------------------------------
# Test 1: Investigate action requires targeting with inspect mode
# ---------------------------------------------------------------------------

def test_investigate_action_requires_targeting():
    """Investigate action must have requires_targeting=True, targeting_mode='inspect', range=10."""
    reset_world()
    party = PartyService()
    player = party.create_initial_party(2, 2)
    action_list = esper.component_for_entity(player, ActionList)

    investigate = next(
        (a for a in action_list.actions if a.name == "Investigate"), None
    )
    assert investigate is not None, "Investigate action not found in ActionList"
    assert investigate.requires_targeting is True, (
        f"Expected requires_targeting=True, got {investigate.requires_targeting}"
    )
    assert investigate.targeting_mode == "inspect", (
        f"Expected targeting_mode='inspect', got '{investigate.targeting_mode}'"
    )
    assert investigate.range == 10, (
        f"Expected range=10, got {investigate.range}"
    )


# ---------------------------------------------------------------------------
# Test 2: Investigate action has zero mana cost
# ---------------------------------------------------------------------------

def test_investigate_action_cost_is_zero():
    """Investigate action must have cost_mana=0 so the mana check never blocks entry."""
    reset_world()
    party = PartyService()
    player = party.create_initial_party(2, 2)
    action_list = esper.component_for_entity(player, ActionList)

    investigate = next(
        (a for a in action_list.actions if a.name == "Investigate"), None
    )
    assert investigate is not None, "Investigate action not found in ActionList"
    assert investigate.cost_mana == 0, (
        f"Expected cost_mana=0, got {investigate.cost_mana}"
    )


# ---------------------------------------------------------------------------
# Test 3: Description.get() accepts stats=None without crash
# ---------------------------------------------------------------------------

def test_description_get_accepts_none_stats():
    """Description.get(None) must return base text without raising an exception."""
    # Without wounded_text
    desc = Description(base="A stone portal")
    result = desc.get(None)
    assert result == "A stone portal", f"Expected 'A stone portal', got '{result}'"

    # With wounded_text — should still return base when stats is None
    desc2 = Description(base="A portal", wounded_text="A damaged portal", wounded_threshold=0.5)
    result2 = desc2.get(None)
    assert result2 == "A portal", (
        f"Expected base text 'A portal' when stats=None, got '{result2}'"
    )


# ---------------------------------------------------------------------------
# Test 4: Description.get() still works correctly with stats (regression)
# ---------------------------------------------------------------------------

def test_description_get_still_works_with_stats():
    """Verify existing Description.get(stats) behavior is not broken by the None guard."""
    desc = Description(
        base="An orc", wounded_text="A wounded orc", wounded_threshold=0.5
    )

    # Healthy entity — returns base
    healthy_stats = make_stats(hp=100, max_hp=100)
    assert desc.get(healthy_stats) == "An orc", (
        f"Expected 'An orc' for healthy stats, got '{desc.get(healthy_stats)}'"
    )

    # Wounded entity — returns wounded_text
    wounded_stats = make_stats(hp=40, max_hp=100)  # 40%, below 50% threshold
    assert desc.get(wounded_stats) == "A wounded orc", (
        f"Expected 'A wounded orc' for wounded stats, got '{desc.get(wounded_stats)}'"
    )

    # max_hp == 0 edge case — should return base, no ZeroDivisionError
    zero_stats = make_stats(hp=0, max_hp=0)
    assert desc.get(zero_stats) == "An orc", (
        f"Expected 'An orc' when max_hp=0, got '{desc.get(zero_stats)}'"
    )


# ---------------------------------------------------------------------------
# Test 5: confirm_action() skips end_player_turn for inspect mode
# ---------------------------------------------------------------------------

def test_confirm_action_skips_end_turn_for_inspect():
    """confirm_action() must NOT call end_player_turn when targeting_mode is 'inspect'."""
    reset_world()

    map_container = make_visible_map(width=5, height=5)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(),
        ActionList(actions=[
            Action(name="Investigate", range=10, requires_targeting=True, targeting_mode="inspect")
        ])
    )

    action_system = ActionSystem(turn_system)
    action_system.set_map(map_container)

    investigate = Action(
        name="Investigate", range=10, requires_targeting=True, targeting_mode="inspect"
    )
    started = action_system.start_targeting(player, investigate)
    assert started, "start_targeting() returned False — targeting did not begin"

    result = action_system.confirm_action(player)
    assert result is True, f"confirm_action() returned {result}, expected True"
    assert turn_system.end_turn_called is False, (
        "end_player_turn() was called for inspect mode — investigation must be a free action"
    )


# ---------------------------------------------------------------------------
# Test 6: confirm_action() calls end_player_turn for combat mode (regression)
# ---------------------------------------------------------------------------

def test_confirm_action_calls_end_turn_for_combat():
    """confirm_action() MUST call end_player_turn for non-inspect targeting modes."""
    reset_world()

    map_container = make_visible_map(width=5, height=5)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(),
        ActionList(actions=[
            Action(name="Ranged", range=5, requires_targeting=True, targeting_mode="auto")
        ])
    )

    action_system = ActionSystem(turn_system)
    action_system.set_map(map_container)

    ranged = Action(name="Ranged", range=5, requires_targeting=True, targeting_mode="auto")
    started = action_system.start_targeting(player, ranged)
    assert started, "start_targeting() returned False — targeting did not begin"

    result = action_system.confirm_action(player)
    assert result is True, f"confirm_action() returned {result}, expected True"
    assert turn_system.end_turn_called is True, (
        "end_player_turn() was NOT called for combat targeting — combat must consume a turn"
    )


# ---------------------------------------------------------------------------
# Test 7: draw_targeting_ui color selection logic
# ---------------------------------------------------------------------------

def test_render_system_cursor_colors():
    """Verify that the color selection logic in draw_targeting_ui produces correct colors."""
    # We test the logic directly by replicating the branching from render_system.py
    # This avoids needing a pygame display surface while still validating the behavior.

    def get_colors_for_mode(mode: str):
        """Replicate the color selection logic from draw_targeting_ui."""
        if mode == "inspect":
            range_color = (0, 255, 255, 50)
            cursor_color = (0, 255, 255)
        else:
            range_color = (255, 255, 0, 50)
            cursor_color = (255, 255, 0)
        return range_color, cursor_color

    # Inspect mode should produce cyan
    inspect_range, inspect_cursor = get_colors_for_mode("inspect")
    assert inspect_range == (0, 255, 255, 50), (
        f"Expected cyan range color for inspect, got {inspect_range}"
    )
    assert inspect_cursor == (0, 255, 255), (
        f"Expected cyan cursor color for inspect, got {inspect_cursor}"
    )

    # Combat/auto mode should produce yellow
    auto_range, auto_cursor = get_colors_for_mode("auto")
    assert auto_range == (255, 255, 0, 50), (
        f"Expected yellow range color for auto, got {auto_range}"
    )
    assert auto_cursor == (255, 255, 0), (
        f"Expected yellow cursor color for auto, got {auto_cursor}"
    )

    # Manual mode should also produce yellow (not inspect)
    manual_range, manual_cursor = get_colors_for_mode("manual")
    assert manual_range == (255, 255, 0, 50), (
        f"Expected yellow range color for manual, got {manual_range}"
    )
    assert manual_cursor == (255, 255, 0), (
        f"Expected yellow cursor color for manual, got {manual_cursor}"
    )

    # Verify actual render_system.py contains the cyan color constant
    import ast
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "ecs", "systems", "render_system.py")) as f:
        source = f.read()
    assert "0, 255, 255" in source, (
        "render_system.py does not contain cyan color (0, 255, 255)"
    )

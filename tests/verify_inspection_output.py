"""Verification tests for Phase 14 inspection output.

Tests that:
1. TILE-01: Confirming investigation on a VISIBLE tile dispatches tile name (yellow) and description.
2. TILE-02: Confirming investigation on a SHROUDED tile dispatches only the tile name.
3. ENT-01: Entities at a VISIBLE target position are listed in the message log.
4. ENT-02: An entity below its HP wound threshold shows wounded_text instead of base description.
5. ENT-03: Multiple entities at the same position are all listed.
6. ENT-04: Entities without a Stats component (portals, corpses) produce output without crash.
7. Regression guard: The player entity is excluded from their own inspection output.

Run from project root:
    python -m pytest tests/verify_inspection_output.py -v
"""

import sys
import os

# Ensure project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import esper

from ecs.world import get_world, reset_world
from ecs.components import (
    Position, Stats, ActionList, Action, Targeting, Name, Description
)
from ecs.systems.action_system import ActionSystem
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile, VisibilityState
from map.tile_registry import TileRegistry, TileType
from config import SpriteLayer


# ---------------------------------------------------------------------------
# Module-level test tile type registration
# ---------------------------------------------------------------------------

STONE_FLOOR_ID = "test_stone_floor"
STONE_FLOOR_TYPE = TileType(
    id=STONE_FLOOR_ID,
    name="Stone Floor",
    walkable=True,
    transparent=True,
    sprites={SpriteLayer.GROUND: "."},
    color=(200, 200, 200),
    base_description="A cold, uneven stone floor.",
)


def setup_tile_registry():
    """Ensure the test tile type is registered (idempotent)."""
    TileRegistry.register(STONE_FLOOR_TYPE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_stats(hp: int = 100, max_hp: int = 100, perception: int = 10) -> Stats:
    return Stats(
        hp=hp, max_hp=max_hp, power=5, defense=2,
        mana=50, max_mana=50, perception=perception, intelligence=10
    )


def make_map_with_visibility(width: int, height: int, visibility_map,
                              tile_type_ids=None) -> MapContainer:
    """Build a MapContainer with controlled visibility and optional tile type IDs.

    Args:
        width: number of columns.
        height: number of rows.
        visibility_map: 2D list (row-major) of VisibilityState values, or a single
                        VisibilityState to use for every tile.
        tile_type_ids: optional 2D list (row-major) of tile type ID strings or None.
                       When provided, sets tile._type_id directly (bypasses Tile()
                       constructor validation so tests can control registry state).
    """
    if isinstance(visibility_map, VisibilityState):
        uniform = visibility_map
        visibility_map = [[uniform] * width for _ in range(height)]

    tiles = [[Tile() for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            tiles[y][x].visibility_state = visibility_map[y][x]
            if tile_type_ids is not None and tile_type_ids[y][x] is not None:
                # Set _type_id directly — avoids constructor re-validation.
                tiles[y][x]._type_id = tile_type_ids[y][x]

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


def make_inspect_action() -> Action:
    return Action(
        name="Investigate",
        cost_mana=0,
        range=10,
        requires_targeting=True,
        targeting_mode="inspect",
    )


# ---------------------------------------------------------------------------
# Message capture fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_world_and_capture(monkeypatch):
    """Reset ECS world and register a log_message capture handler before each test."""
    reset_world()
    setup_tile_registry()

    captured_messages = []

    def capture_handler(text):
        captured_messages.append(text)

    esper.set_handler("log_message", capture_handler)

    yield captured_messages


# ---------------------------------------------------------------------------
# Test 1: TILE-01 — VISIBLE tile shows name (yellow) and description
# ---------------------------------------------------------------------------

def test_visible_tile_shows_name_and_description(fresh_world_and_capture):
    """Confirming inspection on a VISIBLE tile dispatches tile name in yellow and tile description."""
    captured = fresh_world_and_capture

    type_ids = [[STONE_FLOOR_ID] * 5 for _ in range(5)]
    map_container = make_map_with_visibility(5, 5, VisibilityState.VISIBLE, tile_type_ids=type_ids)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(),
    )

    action_system = ActionSystem(map_container, turn_system)
    action_system.start_targeting(player, make_inspect_action())

    result = action_system.confirm_action(player)
    assert result is True, "confirm_action() returned False for a VISIBLE tile"

    # Tile name must appear with yellow color tag
    assert any("[color=yellow]Stone Floor[/color]" in msg for msg in captured), (
        f"Expected '[color=yellow]Stone Floor[/color]' in messages, got: {captured}"
    )
    # Tile description must also appear
    assert any("A cold, uneven stone floor." in msg for msg in captured), (
        f"Expected tile description in messages, got: {captured}"
    )


# ---------------------------------------------------------------------------
# Test 2: TILE-02 — SHROUDED tile shows name only (no description, no entities)
# ---------------------------------------------------------------------------

def test_shrouded_tile_shows_name_only(fresh_world_and_capture):
    """Confirming inspection on a SHROUDED tile dispatches tile name but not description or entities."""
    captured = fresh_world_and_capture

    # 5x5 map: all VISIBLE, target tile at (3,2) is SHROUDED
    vis = [[VisibilityState.VISIBLE] * 5 for _ in range(5)]
    vis[2][3] = VisibilityState.SHROUDED
    type_ids = [[STONE_FLOOR_ID] * 5 for _ in range(5)]
    map_container = make_map_with_visibility(5, 5, vis, tile_type_ids=type_ids)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(),
    )

    # Place an entity on the shrouded tile that should NOT appear
    _orc = esper.create_entity(
        Position(3, 2),
        Name("Orc"),
        Description(base="A menacing orc."),
    )

    action_system = ActionSystem(map_container, turn_system)
    action_system.start_targeting(player, make_inspect_action())

    # Move cursor to (3,2) — the SHROUDED tile
    action_system.move_cursor(player, 1, 0)

    result = action_system.confirm_action(player)
    assert result is True, "confirm_action() returned False for a SHROUDED tile"

    # Tile name must appear
    assert any("[color=yellow]Stone Floor[/color]" in msg for msg in captured), (
        f"Expected tile name in messages, got: {captured}"
    )
    # Tile description must NOT appear
    assert not any("A cold, uneven stone floor." in msg for msg in captured), (
        f"Tile description should not appear for SHROUDED tile, got: {captured}"
    )
    # Entity name must NOT appear
    assert not any("Orc" in msg for msg in captured), (
        f"Entity name should not appear for SHROUDED tile, got: {captured}"
    )


# ---------------------------------------------------------------------------
# Test 3: ENT-01 — Entity at VISIBLE tile is listed
# ---------------------------------------------------------------------------

def test_entity_listed_at_visible_tile(fresh_world_and_capture):
    """An entity with Name and Description at the VISIBLE target position must be listed."""
    captured = fresh_world_and_capture

    type_ids = [[STONE_FLOOR_ID] * 5 for _ in range(5)]
    map_container = make_map_with_visibility(5, 5, VisibilityState.VISIBLE, tile_type_ids=type_ids)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(),
    )

    _orc = esper.create_entity(
        Position(2, 2),
        Name("Orc"),
        Description(base="A menacing orc."),
        make_stats(),
    )

    action_system = ActionSystem(map_container, turn_system)
    action_system.start_targeting(player, make_inspect_action())

    result = action_system.confirm_action(player)
    assert result is True

    # Entity name and description are now dispatched as separate messages.
    assert any("[color=yellow]Orc[/color]" in msg for msg in captured), (
        f"Expected entity name in yellow, got: {captured}"
    )
    assert any("A menacing orc." in msg for msg in captured), (
        f"Expected entity description in messages, got: {captured}"
    )


# ---------------------------------------------------------------------------
# Test 4: ENT-02 — Wounded entity shows wounded_text
# ---------------------------------------------------------------------------

def test_wounded_entity_shows_wounded_text(fresh_world_and_capture):
    """An entity below its HP wound threshold shows wounded_text instead of base description."""
    captured = fresh_world_and_capture

    type_ids = [[STONE_FLOOR_ID] * 5 for _ in range(5)]
    map_container = make_map_with_visibility(5, 5, VisibilityState.VISIBLE, tile_type_ids=type_ids)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(),
    )

    # Orc at hp=3/max_hp=10 — below 0.5 threshold
    wounded_orc_stats = Stats(
        hp=3, max_hp=10, power=5, defense=2,
        mana=0, max_mana=0, perception=3, intelligence=1,
    )
    _orc = esper.create_entity(
        Position(2, 2),
        Name("Orc"),
        Description(
            base="A menacing orc.",
            wounded_text="The orc looks wounded.",
            wounded_threshold=0.5,
        ),
        wounded_orc_stats,
    )

    action_system = ActionSystem(map_container, turn_system)
    action_system.start_targeting(player, make_inspect_action())

    result = action_system.confirm_action(player)
    assert result is True

    assert any("The orc looks wounded." in msg for msg in captured), (
        f"Expected wounded text in messages, got: {captured}"
    )
    assert not any("A menacing orc." in msg for msg in captured), (
        f"Base description should not appear for wounded entity, got: {captured}"
    )


# ---------------------------------------------------------------------------
# Test 5: ENT-03 — Multiple entities all listed
# ---------------------------------------------------------------------------

def test_multiple_entities_all_listed(fresh_world_and_capture):
    """All entities at the VISIBLE target position must be listed in the message log."""
    captured = fresh_world_and_capture

    type_ids = [[STONE_FLOOR_ID] * 5 for _ in range(5)]
    map_container = make_map_with_visibility(5, 5, VisibilityState.VISIBLE, tile_type_ids=type_ids)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(),
    )

    _orc = esper.create_entity(
        Position(2, 2),
        Name("Orc"),
        Description(base="A menacing orc."),
        make_stats(),
    )
    _goblin = esper.create_entity(
        Position(2, 2),
        Name("Goblin"),
        Description(base="A sneaky goblin."),
        make_stats(),
    )

    action_system = ActionSystem(map_container, turn_system)
    action_system.start_targeting(player, make_inspect_action())

    result = action_system.confirm_action(player)
    assert result is True

    assert any("Orc" in msg for msg in captured), (
        f"Expected 'Orc' in messages, got: {captured}"
    )
    assert any("Goblin" in msg for msg in captured), (
        f"Expected 'Goblin' in messages, got: {captured}"
    )


# ---------------------------------------------------------------------------
# Test 6: ENT-04 — Entity without Stats component does not crash
# ---------------------------------------------------------------------------

def test_entity_without_stats_no_crash(fresh_world_and_capture):
    """Entities without a Stats component (portals, corpses) produce output without crash."""
    captured = fresh_world_and_capture

    type_ids = [[STONE_FLOOR_ID] * 5 for _ in range(5)]
    map_container = make_map_with_visibility(5, 5, VisibilityState.VISIBLE, tile_type_ids=type_ids)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(),
    )

    # Portal entity — has Name and Description but NO Stats
    _portal = esper.create_entity(
        Position(2, 2),
        Name("Mysterious Portal"),
        Description(base="A shimmering gateway."),
    )

    action_system = ActionSystem(map_container, turn_system)
    action_system.start_targeting(player, make_inspect_action())

    # Must not raise any exception
    result = action_system.confirm_action(player)
    assert result is True

    assert any("Mysterious Portal" in msg for msg in captured), (
        f"Expected 'Mysterious Portal' in messages, got: {captured}"
    )
    assert any("A shimmering gateway." in msg for msg in captured), (
        f"Expected portal description in messages, got: {captured}"
    )


# ---------------------------------------------------------------------------
# Test 7: Regression guard — player excluded from own inspection
# ---------------------------------------------------------------------------

def test_player_excluded_from_own_inspection(fresh_world_and_capture):
    """The player entity must not appear in their own inspection output."""
    captured = fresh_world_and_capture

    type_ids = [[STONE_FLOOR_ID] * 5 for _ in range(5)]
    map_container = make_map_with_visibility(5, 5, VisibilityState.VISIBLE, tile_type_ids=type_ids)
    turn_system = MockTurnSystem()

    player = esper.create_entity(
        Position(2, 2),
        make_stats(),
        Name("Hero"),
        Description(base="A brave adventurer."),
    )

    action_system = ActionSystem(map_container, turn_system)
    action_system.start_targeting(player, make_inspect_action())

    # Player inspects their own tile (target == origin == (2,2))
    result = action_system.confirm_action(player)
    assert result is True

    # Player's own name must NOT appear in captured messages
    assert not any("Hero" in msg for msg in captured), (
        f"Player name 'Hero' should not appear in own inspection output, got: {captured}"
    )
    assert not any("A brave adventurer." in msg for msg in captured), (
        f"Player description should not appear in own inspection output, got: {captured}"
    )

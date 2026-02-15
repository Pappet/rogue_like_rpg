import esper
import pytest
from ecs.world import reset_world
from ecs.components import AI, AIBehaviorState, AIState, Alignment, Position, Blocker, Corpse
from ecs.systems.ai_system import AISystem
from ecs.systems.turn_system import TurnSystem
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile
from services.resource_loader import ResourceLoader
from config import GameStates

TILE_FILE = "assets/data/tile_types.json"


def make_walkable_map(width=5, height=5):
    """Creates a minimal MapContainer for testing — open floor with wall border."""
    ResourceLoader.load_tiles(TILE_FILE)  # Required before Tile(type_id=...) can be used
    tiles = [[Tile(type_id="floor_stone") for _ in range(width)] for _ in range(height)]
    for x in range(width):
        tiles[0][x] = Tile(type_id="wall_stone")
        tiles[height - 1][x] = Tile(type_id="wall_stone")
    for y in range(height):
        tiles[y][0] = Tile(type_id="wall_stone")
        tiles[y][width - 1] = Tile(type_id="wall_stone")
    return MapContainer([MapLayer(tiles)])


def test_npc_wander_moves_to_adjacent_cardinal_tile():
    """WNDR-01: NPC in WANDER state moves to an adjacent cardinal tile each turn."""
    reset_world()
    map_c = make_walkable_map()
    turn = TurnSystem()
    turn.end_player_turn()

    ent = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(2, 2, layer=0),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0)

    pos = esper.component_for_entity(ent, Position)
    # Exactly one cardinal step from (2, 2)
    assert (abs(pos.x - 2) + abs(pos.y - 2)) == 1, (
        "NPC must move exactly one cardinal step"
    )


def test_npc_wander_never_moves_to_unwalkable_tile():
    """WNDR-02: Wander movement checks tile walkability before moving."""
    reset_world()
    ResourceLoader.load_tiles(TILE_FILE)
    # 3x3 map: walls on N, E, W — only S is walkable
    tiles = [
        [Tile(type_id="wall_stone"), Tile(type_id="wall_stone"), Tile(type_id="wall_stone")],
        [Tile(type_id="wall_stone"), Tile(type_id="floor_stone"), Tile(type_id="wall_stone")],
        [Tile(type_id="floor_stone"), Tile(type_id="floor_stone"), Tile(type_id="floor_stone")],
    ]
    map_c = MapContainer([MapLayer(tiles)])

    turn = TurnSystem()
    turn.end_player_turn()

    ent = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(1, 1, layer=0),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0)

    pos = esper.component_for_entity(ent, Position)
    # Must move south (the only walkable direction)
    assert pos.x == 1 and pos.y == 2, "NPC must only move to walkable tiles"


def test_npc_skips_turn_when_all_adjacent_blocked():
    """WNDR-03: NPC skips turn if all adjacent tiles are blocked — no error."""
    reset_world()
    ResourceLoader.load_tiles(TILE_FILE)
    # 3x3 map: center floor surrounded by walls
    tiles = [
        [Tile(type_id="wall_stone"), Tile(type_id="wall_stone"), Tile(type_id="wall_stone")],
        [Tile(type_id="wall_stone"), Tile(type_id="floor_stone"), Tile(type_id="wall_stone")],
        [Tile(type_id="wall_stone"), Tile(type_id="wall_stone"), Tile(type_id="wall_stone")],
    ]
    map_c = MapContainer([MapLayer(tiles)])

    turn = TurnSystem()
    turn.end_player_turn()

    ent = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(1, 1, layer=0),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0)  # Must not raise

    pos = esper.component_for_entity(ent, Position)
    assert pos.x == 1 and pos.y == 1, "NPC must not move when surrounded by walls"
    assert turn.current_state == GameStates.PLAYER_TURN, "Turn must still end"


def test_two_npcs_do_not_stack_on_same_tile():
    """WNDR-04: Two NPCs cannot move to the same tile in one turn."""
    reset_world()
    map_c = make_walkable_map(width=5, height=5)
    turn = TurnSystem()
    turn.end_player_turn()

    # Two NPCs with Blocker — placed near center with open space between
    ent1 = esper.create_entity(
        AI(), Blocker(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(1, 2, layer=0),
    )
    ent2 = esper.create_entity(
        AI(), Blocker(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(3, 2, layer=0),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0)

    pos1 = esper.component_for_entity(ent1, Position)
    pos2 = esper.component_for_entity(ent2, Position)
    assert (pos1.x, pos1.y) != (pos2.x, pos2.y), (
        "Two NPCs must not occupy the same tile after one turn"
    )


def test_npc_wander_blocked_by_entity_blocker():
    """WNDR-02: Wander checks entity blockers in addition to tile walkability."""
    reset_world()
    map_c = make_walkable_map(width=5, height=5)
    turn = TurnSystem()
    turn.end_player_turn()

    # Blocker entities on all cardinal neighbors of (2, 2)
    for bx, by in [(2, 1), (2, 3), (1, 2), (3, 2)]:
        esper.create_entity(Position(bx, by, layer=0), Blocker())

    ent = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(2, 2, layer=0),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0)

    pos = esper.component_for_entity(ent, Position)
    assert pos.x == 2 and pos.y == 2, (
        "NPC must not move when all adjacent tiles have blocker entities"
    )
    assert turn.current_state == GameStates.PLAYER_TURN, "Turn must still end"

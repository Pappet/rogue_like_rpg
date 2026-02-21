import esper
import pytest
from ecs.world import reset_world
from ecs.components import (
    AI, AIBehaviorState, AIState, Alignment, Position, Blocker, Corpse,
    ChaseData, Name, Stats,
)
from ecs.systems.ai_system import AISystem
from ecs.systems.turn_system import TurnSystem
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile
from services.resource_loader import ResourceLoader
from config import GameStates

TILE_FILE = "assets/data/tile_types.json"


def make_walkable_map(width=10, height=10):
    """Creates a MapContainer for chase tests — open floor with wall border."""
    ResourceLoader.load_tiles(TILE_FILE)
    tiles = [[Tile(type_id="floor_stone") for _ in range(width)] for _ in range(height)]
    for x in range(width):
        tiles[0][x] = Tile(type_id="wall_stone")
        tiles[height - 1][x] = Tile(type_id="wall_stone")
    for y in range(height):
        tiles[y][0] = Tile(type_id="wall_stone")
        tiles[y][width - 1] = Tile(type_id="wall_stone")
    return MapContainer([MapLayer(tiles)])


def make_default_stats(perception=5):
    """Create a minimal Stats component for testing."""
    return Stats(
        hp=10, max_hp=10, power=5, defense=2,
        mana=0, max_mana=0,
        perception=perception, intelligence=5,
    )


def test_hostile_npc_transitions_to_chase_on_seeing_player():
    """CHAS-01, CHAS-03: Hostile NPC within perception range with LOS transitions to CHASE."""
    reset_world()
    map_c = make_walkable_map(width=10, height=10)
    turn = TurnSystem()
    turn.end_player_turn()

    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(3, 3, layer=0),
        make_default_stats(perception=5),
        Name("goblin"),
    )

    player = esper.create_entity(
        Position(5, 3, layer=0),
        make_default_stats(perception=5),
        Blocker(),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0, player_entity=player)

    behavior = esper.component_for_entity(npc, AIBehaviorState)
    assert behavior.state == AIState.CHASE, (
        f"Expected CHASE state, got {behavior.state}"
    )
    assert esper.has_component(npc, ChaseData), (
        "NPC must have ChaseData after transitioning to CHASE"
    )


def test_notices_message_fires_once():
    """CHAS-04: 'notices you' message fires exactly once on first detection, not on subsequent turns."""
    reset_world()
    map_c = make_walkable_map(width=10, height=10)
    turn = TurnSystem()

    messages = []

    def capture_message(msg, *args):
        messages.append(msg)

    esper.set_handler("log_message", capture_message)

    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(3, 3, layer=0),
        make_default_stats(perception=5),
        Name("goblin"),
    )

    player = esper.create_entity(
        Position(5, 3, layer=0),
        make_default_stats(perception=5),
        Blocker(),
    )

    ai_sys = AISystem()

    # Turn 1: NPC should notice player and fire message
    turn.end_player_turn()
    ai_sys.process(turn, map_c, player_layer=0, player_entity=player)

    notices_count = sum(1 for m in messages if "notices you" in m)
    assert notices_count == 1, (
        f"Expected exactly 1 'notices you' message on turn 1, got {notices_count}. Messages: {messages}"
    )

    # Turn 2: NPC already in CHASE — detection block skipped — no new "notices you"
    messages.clear()
    turn.end_player_turn()
    ai_sys.process(turn, map_c, player_layer=0, player_entity=player)

    notices_count_2 = sum(1 for m in messages if "notices you" in m)
    assert notices_count_2 == 0, (
        f"Expected 0 'notices you' messages on turn 2, got {notices_count_2}. Messages: {messages}"
    )


def test_chase_npc_moves_toward_player():
    """CHAS-02: NPC in CHASE state takes one greedy Manhattan step toward the player."""
    reset_world()
    map_c = make_walkable_map(width=10, height=10)
    turn = TurnSystem()
    turn.end_player_turn()

    # NPC already in CHASE at (2,5), player at (8,5) — NPC perception 5, player at distance 6
    # Player is out of perception range so NPC chases last_known position
    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.CHASE, alignment=Alignment.HOSTILE),
        Position(2, 5, layer=0),
        make_default_stats(perception=5),
        Name("goblin"),
        ChaseData(last_known_x=8, last_known_y=5),
    )

    player = esper.create_entity(
        Position(8, 5, layer=0),
        make_default_stats(perception=5),
        Blocker(),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0, player_entity=player)

    pos = esper.component_for_entity(npc, Position)
    assert pos.x == 3 and pos.y == 5, (
        f"Expected NPC at (3, 5) after one step east, got ({pos.x}, {pos.y})"
    )


def test_npc_reverts_to_wander_after_losing_sight():
    """CHAS-05: NPC reverts to WANDER after LOSE_SIGHT_TURNS without LOS to player."""
    reset_world()
    ResourceLoader.load_tiles(TILE_FILE)

    # 10x10 map with wall column at x=5 blocking LOS between NPC (x=2) and player (x=8)
    width, height = 10, 10
    tiles = [[Tile(type_id="floor_stone") for _ in range(width)] for _ in range(height)]
    # Border walls
    for x in range(width):
        tiles[0][x] = Tile(type_id="wall_stone")
        tiles[height - 1][x] = Tile(type_id="wall_stone")
    for y in range(height):
        tiles[y][0] = Tile(type_id="wall_stone")
        tiles[y][width - 1] = Tile(type_id="wall_stone")
    # Wall column at x=5, y=1 to y=3 to block LOS
    for wy in range(1, 4):
        tiles[wy][5] = Tile(type_id="wall_stone")

    map_c = MapContainer([MapLayer(tiles)])
    turn = TurnSystem()
    turn.end_player_turn()

    # NPC at (2,2), already lost sight for 2 turns (one more turn will hit LOSE_SIGHT_TURNS=3)
    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.CHASE, alignment=Alignment.HOSTILE),
        Position(2, 2, layer=0),
        make_default_stats(perception=5),
        Name("goblin"),
        ChaseData(last_known_x=8, last_known_y=2, turns_without_sight=2),
    )

    # Player behind the wall — LOS blocked
    player = esper.create_entity(
        Position(8, 2, layer=0),
        make_default_stats(perception=5),
        Blocker(),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0, player_entity=player)

    behavior = esper.component_for_entity(npc, AIBehaviorState)
    assert behavior.state == AIState.WANDER, (
        f"Expected WANDER state after losing sight, got {behavior.state}"
    )
    assert not esper.has_component(npc, ChaseData), (
        "ChaseData must be removed when NPC reverts to WANDER"
    )


def test_chase_data_stores_coordinates_not_entity_ids():
    """SAFE-01: ChaseData stores tile coordinates only — no entity IDs."""
    reset_world()
    map_c = make_walkable_map(width=10, height=10)
    turn = TurnSystem()
    turn.end_player_turn()

    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(3, 3, layer=0),
        make_default_stats(perception=5),
        Name("goblin"),
    )

    player = esper.create_entity(
        Position(5, 3, layer=0),
        make_default_stats(perception=5),
        Blocker(),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0, player_entity=player)

    assert esper.has_component(npc, ChaseData), "NPC must be in CHASE state with ChaseData"
    chase_data = esper.component_for_entity(npc, ChaseData)
    player_pos = esper.component_for_entity(player, Position)

    assert chase_data.last_known_x == player_pos.x, (
        f"last_known_x {chase_data.last_known_x} != player x {player_pos.x}"
    )
    assert chase_data.last_known_y == player_pos.y, (
        f"last_known_y {chase_data.last_known_y} != player y {player_pos.y}"
    )
    assert not hasattr(chase_data, "player_entity"), (
        "ChaseData must not store player_entity"
    )
    assert not hasattr(chase_data, "target_entity"), (
        "ChaseData must not store target_entity"
    )


def test_friendly_npc_does_not_chase():
    """CHAS-01 implicit: Only HOSTILE NPCs enter CHASE — FRIENDLY NPCs are unaffected."""
    reset_world()
    map_c = make_walkable_map(width=10, height=10)
    turn = TurnSystem()
    turn.end_player_turn()

    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.FRIENDLY),
        Position(3, 3, layer=0),
        make_default_stats(perception=5),
        Name("villager"),
    )

    player = esper.create_entity(
        Position(5, 3, layer=0),
        make_default_stats(perception=5),
        Blocker(),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0, player_entity=player)

    behavior = esper.component_for_entity(npc, AIBehaviorState)
    assert behavior.state == AIState.WANDER, (
        f"FRIENDLY NPC must remain in WANDER state, got {behavior.state}"
    )
    assert not esper.has_component(npc, ChaseData), (
        "FRIENDLY NPC must not have ChaseData"
    )

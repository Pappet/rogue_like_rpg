
import sys
import os
import esper
import pytest
from ecs.world import reset_world
from ecs.components import AI, AIBehaviorState, AIState, Alignment, Position, Stats, Blocker, ChaseData, PathData
from ecs.systems.ai_system import AISystem
from ecs.systems.turn_system import TurnSystem
from config import GameStates, SpriteLayer
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_mock_map(width=10, height=10):
    tiles = [[Tile(sprites={SpriteLayer.GROUND: "."}, transparent=True) for _ in range(width)] for _ in range(height)]
    layer = MapLayer(tiles)
    return MapContainer([layer])

def test_chase_uses_pathfinding():
    """Verify that AISystem._chase creates PathData when chasing."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn() # ENEMY_TURN
    
    map_container = create_mock_map()
    
    # Player at 5,5
    player = esper.create_entity(Position(x=5, y=5, layer=0), Blocker())
    
    # NPC at 1,1
    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.CHASE, alignment=Alignment.HOSTILE),
        Position(x=1, y=1, layer=0),
        Stats(hp=10, max_hp=10, power=1, defense=1, mana=0, max_mana=0, perception=10, intelligence=10),
        ChaseData(last_known_x=5, last_known_y=5)
    )
    
    ai_sys = AISystem()
    # Process NPC turn
    ai_sys.process(turn, map_container, player_layer=0, player_entity=player)
    
    # Check if PathData was added
    assert esper.has_component(npc, PathData), "NPC should have PathData component after _chase"
    path_data = esper.component_for_entity(npc, PathData)
    assert len(path_data.path) > 0, "PathData should have a non-empty path"
    assert path_data.destination == (5, 5), "PathData destination should be the player position"
    
    # Check if NPC moved
    pos = esper.component_for_entity(npc, Position)
    assert (pos.x, pos.y) != (1, 1), "NPC should have moved"
    # In cardinal pathfinding, it should move to 1,2 or 2,1
    assert (pos.x, pos.y) in [(1, 2), (2, 1)]

def test_path_invalidation_on_target_move():
    """Verify that PathData is recomputed when target moves."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()
    
    map_container = create_mock_map()
    player = esper.create_entity(Position(x=5, y=5, layer=0), Blocker())
    
    # NPC already has a path to 5,5
    path = [(1, 2), (1, 3)]
    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.CHASE, alignment=Alignment.HOSTILE),
        Position(x=1, y=1, layer=0),
        Stats(hp=10, max_hp=10, power=1, defense=1, mana=0, max_mana=0, perception=10, intelligence=10),
        ChaseData(last_known_x=5, last_known_y=5),
        PathData(path=path, destination=(5, 5))
    )
    
    # Player moves to 6,6
    esper.component_for_entity(player, Position).x = 6
    esper.component_for_entity(player, Position).y = 6
    
    ai_sys = AISystem()
    ai_sys.process(turn, map_container, player_layer=0, player_entity=player)
    
    path_data = esper.component_for_entity(npc, PathData)
    assert path_data.destination == (6, 6), "Path destination should have updated to (6, 6)"
    # Path should have been recomputed, so it shouldn't be the old path
    assert path_data.path != path, "Path should have been recomputed"

def test_path_blocked_by_entity():
    """Verify that path is cleared and greedy fallback used when path is blocked."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()
    
    map_container = create_mock_map()
    player = esper.create_entity(Position(x=3, y=1, layer=0), Blocker())
    
    # NPC at 1,1, target 3,1. Path is [(2,1), (3,1)]
    path = [(2, 1), (3, 1)]
    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.CHASE, alignment=Alignment.HOSTILE),
        Position(x=1, y=1, layer=0),
        Stats(hp=10, max_hp=10, power=1, defense=1, mana=0, max_mana=0, perception=10, intelligence=10),
        ChaseData(last_known_x=3, last_known_y=1),
        PathData(path=path, destination=(3, 1))
    )
    
    # Blocker at 2,1
    blocker = esper.create_entity(Position(x=2, y=1, layer=0), Blocker())
    
    ai_sys = AISystem()
    ai_sys.process(turn, map_container, player_layer=0, player_entity=player)
    
    path_data = esper.component_for_entity(npc, PathData)
    # The path should have been cleared because (2,1) is blocked
    assert path_data.path == [], "Path should be cleared when blocked"
    
    # Check that NPC stayed in place because greedy fallback couldn't find a closer walkable tile
    pos = esper.component_for_entity(npc, Position)
    assert (pos.x, pos.y) == (1, 1), "NPC should stay in place if path and greedy step are blocked"

def test_layer_aware_pathfinding():
    """Verify that pathfinding is layer-aware."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()
    
    # Layer 0: all walkable. Layer 1: all walls except player/npc
    tiles_l0 = [[Tile(sprites={SpriteLayer.GROUND: "."}, transparent=True) for _ in range(5)] for _ in range(5)]
    tiles_l1 = [[Tile(sprites={SpriteLayer.GROUND: "#"}, transparent=False) for _ in range(5)] for _ in range(5)]
    # Make some tiles walkable on l1
    tiles_l1[1][1] = Tile(sprites={SpriteLayer.GROUND: "."}, transparent=True)
    tiles_l1[1][2] = Tile(sprites={SpriteLayer.GROUND: "."}, transparent=True)
    tiles_l1[1][3] = Tile(sprites={SpriteLayer.GROUND: "."}, transparent=True)
    
    map_container = MapContainer([MapLayer(tiles_l0), MapLayer(tiles_l1)])
    
    player = esper.create_entity(Position(x=3, y=1, layer=1), Blocker())
    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.CHASE, alignment=Alignment.HOSTILE),
        Position(x=1, y=1, layer=1),
        Stats(hp=10, max_hp=10, power=1, defense=1, mana=0, max_mana=0, perception=10, intelligence=10),
        ChaseData(last_known_x=3, last_known_y=1)
    )
    
    ai_sys = AISystem()
    ai_sys.process(turn, map_container, player_layer=1, player_entity=player)
    
    path_data = esper.component_for_entity(npc, PathData)
    # On layer 1, it should move to (2,1). On layer 0 it could have moved to (1,2) too but (2,1) is preferred by greedy/A*
    # Actually, on layer 1, (1,2) is a wall, so it MUST go to (2,1).
    assert (esper.component_for_entity(npc, Position).x, esper.component_for_entity(npc, Position).y) == (2, 1)

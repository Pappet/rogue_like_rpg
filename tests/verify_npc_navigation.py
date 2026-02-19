import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import esper
from ecs.systems.ai_system import AISystem
from ecs.components import Position, AI, AIBehaviorState, AIState, Alignment, PathData, ChaseData, Stats, Name, Blocker
from config import GameStates
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile

def create_mock_tile(walkable=True):
    tile = Tile(transparent=True)
    # Manually set walkable for testing since we don't want to load TileRegistry
    tile._walkable = walkable
    return tile

def create_mock_map(width, height, layer_count=1):
    layers = []
    for _ in range(layer_count):
        tiles = [[create_mock_tile() for _ in range(width)] for _ in range(height)]
        layers.append(MapLayer(tiles))
    return MapContainer(layers)

class MockTurnSystem:
    def __init__(self):
        self.current_state = GameStates.ENEMY_TURN
    def end_enemy_turn(self):
        self.current_state = GameStates.PLAYER_TURN

def test_npc_follows_path():
    print("Running test_npc_follows_path...")
    esper.clear_database()
    ai_system = AISystem()
    turn_system = MockTurnSystem()
    map_container = create_mock_map(10, 10)
    
    # NPC at (0,0) with a 3-step route
    path = [(1,0), (2,0), (3,0)]
    npc = esper.create_entity(
        Position(0, 0),
        AI(),
        AIBehaviorState(state=AIState.IDLE, alignment=Alignment.NEUTRAL),
        PathData(path=path, destination=(3,0))
    )
    
    # Step 1
    turn_system.current_state = GameStates.ENEMY_TURN
    ai_system.process(turn_system, map_container, 0)
    pos = esper.component_for_entity(npc, Position)
    assert (pos.x, pos.y) == (1, 0), f"Expected (1, 0), got ({pos.x}, {pos.y})"
    
    # Step 2
    turn_system.current_state = GameStates.ENEMY_TURN
    ai_system.process(turn_system, map_container, 0)
    pos = esper.component_for_entity(npc, Position)
    assert (pos.x, pos.y) == (2, 0), f"Expected (2, 0), got ({pos.x}, {pos.y})"
    
    # Step 3
    turn_system.current_state = GameStates.ENEMY_TURN
    ai_system.process(turn_system, map_container, 0)
    pos = esper.component_for_entity(npc, Position)
    assert (pos.x, pos.y) == (3, 0), f"Expected (3, 0), got ({pos.x}, {pos.y})"
    
    print("test_npc_follows_path passed!")

def test_npc_recomputes_on_target_move():
    print("Running test_npc_recomputes_on_target_move...")
    esper.clear_database()
    ai_system = AISystem()
    turn_system = MockTurnSystem()
    map_container = create_mock_map(10, 10)
    
    player = esper.create_entity(Position(5, 0))
    npc = esper.create_entity(
        Position(0, 0),
        AI(),
        AIBehaviorState(state=AIState.CHASE, alignment=Alignment.HOSTILE),
        ChaseData(last_known_x=5, last_known_y=0),
        Stats(hp=10, max_hp=10, power=5, defense=5, mana=0, max_mana=0, perception=10, intelligence=10)
    )
    
    # Turn 1: NPC moves towards (5,0)
    turn_system.current_state = GameStates.ENEMY_TURN
    ai_system.process(turn_system, map_container, 0, player_entity=player)
    pos = esper.component_for_entity(npc, Position)
    assert (pos.x, pos.y) == (1, 0), f"Expected (1, 0), got ({pos.x}, {pos.y})"
    
    # Move player to (1, 5)
    player_pos = esper.component_for_entity(player, Position)
    player_pos.x = 1
    player_pos.y = 5
    
    # Turn 2: NPC should recompute and move towards (1, 5)
    # Since it was at (1, 0), the next step towards (1, 5) should be (1, 1)
    turn_system.current_state = GameStates.ENEMY_TURN
    ai_system.process(turn_system, map_container, 0, player_entity=player)
    pos = esper.component_for_entity(npc, Position)
    assert (pos.x, pos.y) == (1, 1), f"Expected (1, 1), got ({pos.x}, {pos.y})"
    
    print("test_npc_recomputes_on_target_move passed!")

def test_npc_waits_if_path_blocked():
    print("Running test_npc_waits_if_path_blocked...")
    esper.clear_database()
    ai_system = AISystem()
    turn_system = MockTurnSystem()
    map_container = create_mock_map(10, 10)
    
    # NPC 1 at (0,0) with path to (2,0)
    npc1 = esper.create_entity(
        Position(0, 0),
        AI(),
        AIBehaviorState(state=AIState.IDLE, alignment=Alignment.NEUTRAL),
        PathData(path=[(1,0), (2,0)], destination=(2,0))
    )
    
    # NPC 2 (blocker) at (1,0)
    npc2 = esper.create_entity(
        Position(1, 0),
        Blocker()
    )
    
    # Turn 1: NPC 1 should not move to (1,0) because it's blocked
    turn_system.current_state = GameStates.ENEMY_TURN
    ai_system.process(turn_system, map_container, 0)
    pos1 = esper.component_for_entity(npc1, Position)
    assert (pos1.x, pos1.y) == (0, 0), f"NPC1 moved to blocked tile: ({pos1.x}, {pos1.y})"
    
    # Path should be invalidated (cleared) because it was blocked by entity
    path_data = esper.component_for_entity(npc1, PathData)
    assert path_data.path == [], f"Path should be cleared, but got {path_data.path}"
    
    print("test_npc_waits_if_path_blocked passed!")

if __name__ == "__main__":
    try:
        test_npc_follows_path()
        test_npc_recomputes_on_target_move()
        test_npc_waits_if_path_blocked()
        print("\nAll NPC navigation integration tests passed!")
    except AssertionError as e:
        print(f"\nIntegration Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

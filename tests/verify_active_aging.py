import sys
import os
import esper

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ecs.systems.visibility_system import VisibilitySystem
from ecs.systems.turn_system import TurnSystem
from ecs.components import Position, Stats
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile, VisibilityState

def test_active_aging():
    # Setup world
    esper.clear_database()
    
    # Setup map
    tile1 = Tile(transparent=True, dark=False)
    tile1.visibility_state = VisibilityState.SHROUDED
    tile1.rounds_since_seen = 2
    
    tile2 = Tile(transparent=True, dark=False)
    tile2.visibility_state = VisibilityState.VISIBLE
    tile2.rounds_since_seen = 0
    
    layer = MapLayer([[tile1, tile2]])
    container = MapContainer([layer])
    
    # Setup systems
    turn_system = TurnSystem()
    visibility_system = VisibilitySystem(container, turn_system)
    esper.add_processor(visibility_system)
    
    # Setup player
    player = esper.create_entity()
    esper.add_component(player, Position(x=1, y=0)) # See tile 2
    # perception=0 means only seeing current tile (1,0)
    esper.add_component(player, Stats(hp=10, max_hp=10, power=5, defense=2, mana=10, max_mana=10, perception=0, intelligence=2))
    # Threshold = 2 * 5 = 10
    
    print("Initial state:")
    print(f"Tile 1: {tile1.visibility_state}, age: {tile1.rounds_since_seen}")
    print(f"Tile 2: {tile2.visibility_state}, age: {tile2.rounds_since_seen}")
    
    # Run process (Turn 1)
    esper.process()
    print("\nAfter Turn 1 process:")
    print(f"Tile 1: {tile1.visibility_state}, age: {tile1.rounds_since_seen}")
    print(f"Tile 2: {tile2.visibility_state}, age: {tile2.rounds_since_seen}")
    
    # Tile 2 should be VISIBLE because player is there (perception 0 still includes current tile)
    assert tile2.visibility_state == VisibilityState.VISIBLE
    # Tile 1 should still be SHROUDED
    assert tile1.visibility_state == VisibilityState.SHROUDED
    assert tile1.rounds_since_seen == 2
    
    # Advance turn
    turn_system.end_player_turn()
    turn_system.end_enemy_turn() # round_counter becomes 2
    
    esper.process()
    print("\nAfter Turn 2 process:")
    print(f"Tile 1: {tile1.visibility_state}, age: {tile1.rounds_since_seen}")
    print(f"Tile 2: {tile2.visibility_state}, age: {tile2.rounds_since_seen}")
    
    assert tile1.rounds_since_seen == 3 # Incremented by 1
    
    # Advance 10 more turns
    for _ in range(10):
        turn_system.end_player_turn()
        turn_system.end_enemy_turn()
        esper.process()
        
    print("\nAfter Turn 12 process:")
    print(f"Tile 1: {tile1.visibility_state}, age: {tile1.rounds_since_seen}")
    print(f"Tile 2: {tile2.visibility_state}, age: {tile2.rounds_since_seen}")
    
    assert tile1.visibility_state == VisibilityState.FORGOTTEN
    assert tile2.visibility_state == VisibilityState.VISIBLE # Still seeing it
    
    print("\nTest passed!")

if __name__ == "__main__":
    test_active_aging()
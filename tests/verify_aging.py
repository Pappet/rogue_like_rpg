
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile, VisibilityState

def test_aging():
    # Setup
    tile1 = Tile(transparent=True, dark=False)
    tile1.visibility_state = VisibilityState.SHROUDED
    tile1.rounds_since_seen = 2
    
    tile2 = Tile(transparent=True, dark=False)
    tile2.visibility_state = VisibilityState.VISIBLE
    tile2.rounds_since_seen = 0
    
    layer = MapLayer([[tile1, tile2]])
    container = MapContainer([layer])
    
    print("Initial state:")
    print(f"Tile 1: {tile1.visibility_state}, age: {tile1.rounds_since_seen}")
    print(f"Tile 2: {tile2.visibility_state}, age: {tile2.rounds_since_seen}")
    
    # Test on_exit
    container.on_exit(10)
    print("\nAfter on_exit(10):")
    print(f"Tile 1: {tile1.visibility_state}, age: {tile1.rounds_since_seen}")
    print(f"Tile 2: {tile2.visibility_state}, age: {tile2.rounds_since_seen}")
    
    assert tile2.visibility_state == VisibilityState.SHROUDED
    assert tile2.rounds_since_seen == 0
    assert container.last_visited_turn == 10
    
    # Test on_enter with threshold=11
    # tile1 age was 2, now we add (20-10) = 10. 2 + 10 = 12.
    # tile2 age was 0, now we add (20-10) = 10.
    container.on_enter(20, memory_threshold=11)
    print("\nAfter on_enter(20, threshold=11):")
    print(f"Tile 1: {tile1.visibility_state}, age: {tile1.rounds_since_seen}")
    print(f"Tile 2: {tile2.visibility_state}, age: {tile2.rounds_since_seen}")
    
    assert tile1.visibility_state == VisibilityState.FORGOTTEN
    assert tile2.visibility_state == VisibilityState.SHROUDED
    assert tile2.rounds_since_seen == 10
    
    # Test tile 2 forgotten with threshold=5
    # container.on_enter doesn't update last_visited_turn, so we use a later time
    # turns_passed = 30 - 10 = 20
    # tile2 age becomes 0 + 20 = 20
    container.on_enter(30, memory_threshold=5)
    print("\nAfter on_enter(30, threshold=5):")
    print(f"Tile 2: {tile2.visibility_state}, age: {tile2.rounds_since_seen}")
    assert tile2.visibility_state == VisibilityState.FORGOTTEN

    print("\nTest passed!")

if __name__ == "__main__":
    test_aging()

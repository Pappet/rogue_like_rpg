import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import esper
from services.pathfinding_service import PathfindingService
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile
from ecs.components import Position, Blocker

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

def test_direct_path():
    print("Running test_direct_path...")
    esper.clear_database()
    world = esper
    map_container = create_mock_map(10, 10)
    
    start = (0, 0)
    end = (5, 0)
    
    path = PathfindingService.get_path(world, map_container, start, end)
    
    assert len(path) == 5, f"Expected path length 5, got {len(path)}"
    assert path == [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0)], f"Path mismatch: {path}"
    print("test_direct_path passed!")

def test_obstacle_avoidance():
    print("Running test_obstacle_avoidance...")
    esper.clear_database()
    world = esper
    map_container = create_mock_map(5, 5)
    
    # Create walls at (1,1) and (1,0)
    map_container.layers[0].tiles[1][1]._walkable = False
    map_container.layers[0].tiles[0][1]._walkable = False
    
    start = (0, 0)
    end = (2, 2)
    
    path = PathfindingService.get_path(world, map_container, start, end)
    
    # Valid cardinal path avoiding (1,0) and (1,1)
    # One possibility: (0,1) -> (0,2) -> (1,2) -> (2,2)
    assert len(path) > 0, "No path found"
    for x, y in path:
        assert map_container.is_walkable(x, y), f"Path goes through wall at ({x}, {y})"
    
    assert path[-1] == end, f"Path does not reach end: {path[-1]}"
    print("test_obstacle_avoidance passed!")

def test_entity_blocker():
    print("Running test_entity_blocker...")
    esper.clear_database()
    world = esper
    map_container = create_mock_map(10, 10)
    
    # Entity at (2,0) blocking the way
    world.create_entity(Position(2, 0), Blocker())
    
    start = (0, 0)
    end = (5, 0)
    
    path = PathfindingService.get_path(world, map_container, start, end)
    
    assert len(path) > 5, f"Expected path longer than 5 due to obstacle, got {len(path)}"
    assert (2, 0) not in path, "Path should not go through entity blocker"
    assert path[-1] == end, f"Path does not reach end: {path[-1]}"
    print("test_entity_blocker passed!")

def test_destination_blocker():
    print("Running test_destination_blocker...")
    esper.clear_database()
    world = esper
    map_container = create_mock_map(5, 5)
    
    # Target (2,0) has a blocker
    world.create_entity(Position(2, 0), Blocker())
    
    start = (0, 0)
    end = (2, 0)
    
    path = PathfindingService.get_path(world, map_container, start, end)
    
    assert len(path) == 2, f"Expected path length 2, got {len(path)}"
    # Target IS walkable in PathfindingService.get_path even if blocked
    assert path[-1] == (2, 0), "Path should successfully lead to the blocked destination"
    print("test_destination_blocker passed!")

def test_unreachable():
    print("Running test_unreachable...")
    esper.clear_database()
    world = esper
    map_container = create_mock_map(5, 5)
    
    # Box in (4,4)
    map_container.layers[0].tiles[3][4]._walkable = False
    map_container.layers[0].tiles[4][3]._walkable = False
    map_container.layers[0].tiles[3][3]._walkable = False
    
    start = (0, 0)
    end = (4, 4)
    
    path = PathfindingService.get_path(world, map_container, start, end)
    
    assert path == [], f"Expected empty path for unreachable target, got {path}"
    print("test_unreachable passed!")

if __name__ == "__main__":
    try:
        test_direct_path()
        test_obstacle_avoidance()
        test_entity_blocker()
        test_destination_blocker()
        test_unreachable()
        print("\nAll pathfinding unit tests passed!")
    except AssertionError as e:
        print(f"\nTest FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

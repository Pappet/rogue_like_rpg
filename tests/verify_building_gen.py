import sys
import os
import esper

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.map_service import MapService
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile
from ecs.components import Portal, Position
from config import SpriteLayer

from ecs.world import get_world, reset_world

def test_add_house_to_map():
    reset_world()
    world = get_world()
    map_service = MapService()
    
    # Create an empty MapContainer
    width, height = 20, 20
    tiles = [[Tile(True, False, {}) for _ in range(width)] for _ in range(height)]
    layer = MapLayer(tiles)
    container = MapContainer([layer])
    
    map_service.register_map("TestMap", container)
    
    # Add a house
    map_service.add_house_to_map(world, container, 5, 5, 6, 6, 2)
    
    # Verify layers
    assert len(container.layers) == 2
    
    # Verify walls on Layer 0
    # (5,5) is top-left corner
    assert container.layers[0].tiles[5][5].sprites[SpriteLayer.GROUND] == '#'
    assert container.layers[0].tiles[5][5].transparent is False
    
    # (5+6-1, 5+6-1) = (10,10) is bottom-right corner
    assert container.layers[0].tiles[10][10].sprites[SpriteLayer.GROUND] == '#'
    
    # Verify floor
    assert container.layers[0].tiles[7][7].sprites[SpriteLayer.GROUND] == '.'
    assert container.layers[0].tiles[7][7].transparent is True
    
    # Verify door on Layer 0
    # door_x, door_y = 5 + 6 // 2, 5 + 6 - 1 = 8, 10
    assert container.layers[0].tiles[10][8].sprites[SpriteLayer.GROUND] == '.'
    assert container.layers[0].tiles[10][8].transparent is True
    
    # Verify walls on Layer 1
    assert container.layers[1].tiles[5][5].sprites[SpriteLayer.GROUND] == '#'
    
    # Verify Portals
    portals = world.get_components(Position, Portal)
    portal_count = 0
    stairs_up = False
    stairs_down = False
    
    for ent, (pos, portal) in portals:
        portal_count += 1
        if portal.name == "Stairs Up":
            stairs_up = True
            assert pos.x == 5 + 6 - 2 # 9
            assert pos.y == 5 + 6 - 2 # 9
            assert pos.layer == 0
            assert portal.target_layer == 1
        if portal.name == "Stairs Down":
            stairs_down = True
            assert pos.x == 9
            assert pos.y == 9
            assert pos.layer == 1
            assert portal.target_layer == 0
            
    assert portal_count == 2
    assert stairs_up
    assert stairs_down
    
    print("test_add_house_to_map passed")

if __name__ == "__main__":
    test_add_house_to_map()
    print("All Building Gen tests passed!")

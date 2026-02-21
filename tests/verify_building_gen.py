import sys
import os
import esper

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.map_service import MapService
from services.resource_loader import ResourceLoader
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile
from ecs.components import Portal, Position
from config import SpriteLayer

from ecs.world import get_world, reset_world

TILE_FILE = "assets/data/tile_types.json"


def test_add_house_to_map():
    ResourceLoader.load_tiles(TILE_FILE)
    reset_world()
    world = get_world()
    map_service = MapService()

    # Create an empty MapContainer using registry tiles
    width, height = 20, 20
    tiles = [[Tile(type_id="floor_stone") for _ in range(width)] for _ in range(height)]
    layer = MapLayer(tiles)
    container = MapContainer([layer])

    map_service.register_map("TestMap", container)

    # Add a house: start=(5,5), size=(6,6), 2 floors
    map_service.add_house_to_map(world, container, 5, 5, 6, 6, 2)

    # Verify layers (second layer auto-created by add_house_to_map)
    assert len(container.layers) == 2

    # Verify walls on Layer 0 — corners become wall_stone (sprite '#')
    assert container.layers[0].tiles[5][5].sprites[SpriteLayer.GROUND] == '#'
    assert container.layers[0].tiles[5][5].transparent is False

    # Bottom-right corner
    assert container.layers[0].tiles[10][10].sprites[SpriteLayer.GROUND] == '#'

    # Verify interior floor on Layer 0
    assert container.layers[0].tiles[7][7].sprites[SpriteLayer.GROUND] == '.'
    assert container.layers[0].tiles[7][7].transparent is True

    # Verify walls on Layer 1
    assert container.layers[1].tiles[5][5].sprites[SpriteLayer.GROUND] == '#'

    # Verify Portals — add_house_to_map places Stairs Up (layer 0) and Stairs Down (layer 1)
    # For start=(5,5), w=6, h=6:
    #   sx_up = 5+6-2=9, sy_up = 5+2=7  → Stairs Up at (9,7) layer 0, target layer 1
    #   z=1 is odd so pos_down uses (sx_up, sy_up) = (9,7) → Stairs Down at (9,7) layer 1
    portals = world.get_components(Position, Portal)
    portal_count = 0
    stairs_up = False
    stairs_down = False

    for ent, (pos, portal) in portals:
        portal_count += 1
        if portal.name == "Stairs Up":
            stairs_up = True
            assert pos.x == 9
            assert pos.y == 7
            assert pos.layer == 0
            assert portal.target_layer == 1
        if portal.name == "Stairs Down":
            stairs_down = True
            assert pos.x == 9
            assert pos.y == 7
            assert pos.layer == 1
            assert portal.target_layer == 0

    assert portal_count == 2
    assert stairs_up
    assert stairs_down

    print("test_add_house_to_map passed")


if __name__ == "__main__":
    test_add_house_to_map()
    print("All Building Gen tests passed!")

import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from map.map_layer import MapLayer
from map.tile import Tile
from map.map_generator_utils import draw_rectangle, place_door
from config import SpriteLayer
from services.resource_loader import ResourceLoader

TILE_FILE = "assets/data/tile_types.json"


def test_draw_rectangle():
    ResourceLoader.load_tiles(TILE_FILE)
    # Create a 10x10 MapLayer with legacy blank tiles
    tiles = [[Tile(transparent=True, sprites={SpriteLayer.GROUND: ' '}) for _ in range(10)] for _ in range(10)]
    layer = MapLayer(tiles)

    # Draw a 5x5 hollow rectangle of walls (registry type_id)
    draw_rectangle(layer, 1, 1, 5, 5, 'wall_stone', filled=False)

    # Check corners become wall_stone (sprite '#', transparent False)
    assert layer.tiles[1][1].sprites[SpriteLayer.GROUND] == '#'
    assert layer.tiles[1][5].sprites[SpriteLayer.GROUND] == '#'
    assert layer.tiles[5][1].sprites[SpriteLayer.GROUND] == '#'
    assert layer.tiles[5][5].sprites[SpriteLayer.GROUND] == '#'

    # Check transparency of wall
    assert layer.tiles[1][1].transparent is False

    # Check interior (should be ' ' because filled=False and we initialized with ' ')
    assert layer.tiles[3][3].sprites[SpriteLayer.GROUND] == ' '
    assert layer.tiles[3][3].transparent is True

    # Draw a 3x3 filled rectangle of floors (registry type_id)
    draw_rectangle(layer, 2, 2, 3, 3, 'floor_stone', filled=True)
    assert layer.tiles[3][3].sprites[SpriteLayer.GROUND] == '.'
    assert layer.tiles[3][3].transparent is True
    assert layer.tiles[2][2].sprites[SpriteLayer.GROUND] == '.'

    print("test_draw_rectangle passed")


def test_place_door():
    ResourceLoader.load_tiles(TILE_FILE)
    tiles = [[Tile(transparent=False, sprites={SpriteLayer.GROUND: '#'}) for _ in range(10)] for _ in range(10)]
    layer = MapLayer(tiles)

    # place_door uses 'door_stone' by default (sprite '.', transparent True)
    place_door(layer, 5, 5)
    assert layer.tiles[5][5].sprites[SpriteLayer.GROUND] == '.'
    assert layer.tiles[5][5].transparent is True

    print("test_place_door passed")


if __name__ == "__main__":
    test_draw_rectangle()
    test_place_door()
    print("All Map Utils tests passed!")

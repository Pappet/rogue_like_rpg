import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from map.map_layer import MapLayer
from map.tile import Tile
from map.map_generator_utils import draw_rectangle, place_door
from config import SpriteLayer

def test_draw_rectangle():
    # Create a 10x10 MapLayer
    tiles = [[Tile(True, False, {SpriteLayer.GROUND: ' '}) for _ in range(10)] for _ in range(10)]
    layer = MapLayer(tiles)
    
    # Draw a 5x5 hollow rectangle of walls
    draw_rectangle(layer, 1, 1, 5, 5, '#', filled=False)
    
    # Check corners
    assert layer.tiles[1][1].sprites[SpriteLayer.GROUND] == '#'
    assert layer.tiles[1][5].sprites[SpriteLayer.GROUND] == '#'
    assert layer.tiles[5][1].sprites[SpriteLayer.GROUND] == '#'
    assert layer.tiles[5][5].sprites[SpriteLayer.GROUND] == '#'
    
    # Check transparency
    assert layer.tiles[1][1].transparent is False
    
    # Check interior (should be ' ' because filled=False and we initialized with ' ')
    assert layer.tiles[3][3].sprites[SpriteLayer.GROUND] == ' '
    assert layer.tiles[3][3].transparent is True

    # Draw a 3x3 filled rectangle of floors
    draw_rectangle(layer, 2, 2, 3, 3, '.', filled=True)
    assert layer.tiles[3][3].sprites[SpriteLayer.GROUND] == '.'
    assert layer.tiles[3][3].transparent is True
    assert layer.tiles[2][2].sprites[SpriteLayer.GROUND] == '.'
    
    print("test_draw_rectangle passed")

def test_place_door():
    tiles = [[Tile(False, False, {SpriteLayer.GROUND: '#'}) for _ in range(10)] for _ in range(10)]
    layer = MapLayer(tiles)
    
    place_door(layer, 5, 5, '+')
    assert layer.tiles[5][5].sprites[SpriteLayer.GROUND] == '+'
    assert layer.tiles[5][5].transparent is True
    
    print("test_place_door passed")

if __name__ == "__main__":
    test_draw_rectangle()
    test_place_door()
    print("All Map Utils tests passed!")

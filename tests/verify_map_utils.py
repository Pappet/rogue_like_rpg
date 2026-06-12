import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import SpriteLayer
from game.content.resource_loader import ResourceLoader
from game.map.map_generator_utils import draw_rectangle, get_nearest_walkable_tile, place_door
from game.map.map_layer import MapLayer
from game.map.tile import Tile

TILE_FILE = "assets/data/tile_types.json"


def test_draw_rectangle():
    ResourceLoader.load_tiles(TILE_FILE)
    # Create a 10x10 MapLayer with legacy blank tiles
    tiles = [[Tile(transparent=True, sprites={SpriteLayer.GROUND: " "}) for _ in range(10)] for _ in range(10)]
    layer = MapLayer(tiles)

    # Draw a 5x5 hollow rectangle of walls (registry type_id)
    draw_rectangle(layer, 1, 1, 5, 5, "wall_stone", filled=False)

    # Check corners become wall_stone (sprite '#', transparent False)
    assert layer.tiles[1][1].sprites[SpriteLayer.GROUND] == "#"
    assert layer.tiles[1][5].sprites[SpriteLayer.GROUND] == "#"
    assert layer.tiles[5][1].sprites[SpriteLayer.GROUND] == "#"
    assert layer.tiles[5][5].sprites[SpriteLayer.GROUND] == "#"

    # Check transparency of wall
    assert layer.tiles[1][1].transparent is False

    # Check interior (should be ' ' because filled=False and we initialized with ' ')
    assert layer.tiles[3][3].sprites[SpriteLayer.GROUND] == " "
    assert layer.tiles[3][3].transparent is True

    # Draw a 3x3 filled rectangle of floors (registry type_id)
    draw_rectangle(layer, 2, 2, 3, 3, "floor_stone", filled=True)
    assert layer.tiles[3][3].sprites[SpriteLayer.GROUND] == "."
    assert layer.tiles[3][3].transparent is True
    assert layer.tiles[2][2].sprites[SpriteLayer.GROUND] == "."

    print("test_draw_rectangle passed")


def test_place_door():
    ResourceLoader.load_tiles(TILE_FILE)
    tiles = [[Tile(transparent=False, sprites={SpriteLayer.GROUND: "#"}) for _ in range(10)] for _ in range(10)]
    layer = MapLayer(tiles)

    # place_door uses 'door_stone' by default (sprite '+', transparent True)
    place_door(layer, 5, 5)
    assert layer.tiles[5][5].sprites[SpriteLayer.GROUND] == "+"
    assert layer.tiles[5][5].transparent is True

    print("test_place_door passed")


def test_get_nearest_walkable_skips_excluded_positions():
    """get_nearest_walkable_tile must skip positions listed in excluded_positions."""
    ResourceLoader.load_tiles(TILE_FILE)
    tiles = [[Tile(type_id="floor_stone") for _ in range(5)] for _ in range(5)]
    layer = MapLayer(tiles)

    result = get_nearest_walkable_tile(layer, 2, 2, excluded_positions={(2, 2)})
    assert result != (2, 2), "Must not return an excluded position"
    nx, ny = result
    assert 0 <= nx < 5 and 0 <= ny < 5
    assert layer.tiles[ny][nx].walkable


def test_get_nearest_walkable_avoids_door_tile_in_first_pass():
    """get_nearest_walkable_tile must prefer non-door tiles when avoid_type_ids is set."""
    ResourceLoader.load_tiles(TILE_FILE)
    tiles = [[Tile(type_id="floor_stone") for _ in range(5)] for _ in range(5)]
    tiles[2][2] = Tile(type_id="door_stone")
    layer = MapLayer(tiles)

    result = get_nearest_walkable_tile(layer, 2, 2, avoid_type_ids={"door_stone", "door_wood"})
    nx, ny = result
    assert layer.tiles[ny][nx].type_id not in {"door_stone", "door_wood"}, (
        "Must find a non-door tile when floor tiles are available nearby"
    )


def test_get_nearest_walkable_falls_back_to_door_when_only_option():
    """When the only walkable tile is a door, it must be returned as a fallback."""
    ResourceLoader.load_tiles(TILE_FILE)
    tiles = [
        [Tile(type_id="wall_stone"), Tile(type_id="wall_stone"), Tile(type_id="wall_stone")],
        [Tile(type_id="wall_stone"), Tile(type_id="door_stone"), Tile(type_id="wall_stone")],
        [Tile(type_id="wall_stone"), Tile(type_id="wall_stone"), Tile(type_id="wall_stone")],
    ]
    layer = MapLayer(tiles)

    result = get_nearest_walkable_tile(layer, 1, 1, avoid_type_ids={"door_stone", "door_wood"})
    assert result == (1, 1), "Must fall back to door when it is the only walkable tile"


if __name__ == "__main__":
    test_draw_rectangle()
    test_place_door()
    print("All Map Utils tests passed!")

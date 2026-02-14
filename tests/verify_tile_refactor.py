"""Verification script for the refactored Tile class and map generation pipeline.

Run from project root:
    python3 tests/verify_tile_refactor.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SpriteLayer
from map.tile_registry import TileRegistry
from map.tile import Tile, VisibilityState
from services.resource_loader import ResourceLoader

TILE_FILE = "assets/data/tile_types.json"


def check(description: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}")
    if not condition:
        raise AssertionError(f"Check failed: {description}")


def main():
    print("=== Tile Refactor Verification ===\n")

    TileRegistry.clear()
    ResourceLoader.load_tiles(TILE_FILE)

    # --- Task 1: Tile class uses registry ---
    print("Checking Tile created from type_id='floor_stone'...")
    floor_tile = Tile(type_id="floor_stone")
    check("floor_tile.walkable is True", floor_tile.walkable is True)
    check("floor_tile.transparent is True", floor_tile.transparent is True)
    check("floor_tile has GROUND sprite '.'", floor_tile.sprites.get(SpriteLayer.GROUND) == ".")
    check("floor_tile.visibility_state is UNEXPLORED",
          floor_tile.visibility_state == VisibilityState.UNEXPLORED)
    check("floor_tile.rounds_since_seen == 0", floor_tile.rounds_since_seen == 0)
    print()

    print("Checking Tile created from type_id='wall_stone'...")
    wall_tile = Tile(type_id="wall_stone")
    check("wall_tile.walkable is False", wall_tile.walkable is False)
    check("wall_tile.transparent is False", wall_tile.transparent is False)
    check("wall_tile has GROUND sprite '#'", wall_tile.sprites.get(SpriteLayer.GROUND) == "#")
    print()

    print("Checking Tile.set_type() converts floor to wall...")
    t = Tile(type_id="floor_stone")
    check("Before set_type: walkable True", t.walkable is True)
    t.set_type("wall_stone")
    check("After set_type('wall_stone'): walkable False", t.walkable is False)
    check("After set_type('wall_stone'): transparent False", t.transparent is False)
    print()

    print("Checking sprite dicts are per-instance copies (not shared)...")
    t1 = Tile(type_id="floor_stone")
    t2 = Tile(type_id="floor_stone")
    t1.sprites[SpriteLayer.GROUND] = "X"
    check("Mutating t1 sprites doesn't affect t2", t2.sprites.get(SpriteLayer.GROUND) == ".")
    print()

    print("Checking legacy Tile construction still works...")
    legacy_floor = Tile(transparent=True, dark=False, sprites={SpriteLayer.GROUND: "."})
    check("Legacy floor.walkable is True", legacy_floor.walkable is True)
    legacy_wall = Tile(transparent=False, dark=False, sprites={SpriteLayer.GROUND: "#"})
    check("Legacy wall.walkable is False", legacy_wall.walkable is False)
    print()

    print("Checking error on unknown type_id...")
    try:
        _ = Tile(type_id="nonexistent_tile_type")
        check("ValueError raised for unknown type_id", False)
    except ValueError:
        check("ValueError raised for unknown type_id", True)
    print()

    # --- Task 2 & 3: Map generation uses type_ids ---
    print("Checking map generation with type_ids...")
    from map.map_layer import MapLayer
    from map.map_generator_utils import draw_rectangle, place_door

    # Build a small blank layer with legacy tiles (no type_id yet).
    size = 10
    tiles = []
    for y in range(size):
        row = []
        for x in range(size):
            row.append(Tile(transparent=True, dark=False))
        tiles.append(row)
    layer = MapLayer(tiles)

    draw_rectangle(layer, 0, 0, size, size, "wall_stone", filled=False)
    draw_rectangle(layer, 1, 1, size - 2, size - 2, "floor_stone", filled=True)

    # Border tile should be wall_stone
    border_tile = layer.tiles[0][0]
    check("Border tile walkable is False (wall_stone)", border_tile.walkable is False)
    check("Border tile transparent is False (wall_stone)", border_tile.transparent is False)

    # Interior tile should be floor_stone
    interior_tile = layer.tiles[2][2]
    check("Interior tile walkable is True (floor_stone)", interior_tile.walkable is True)
    check("Interior tile transparent is True (floor_stone)", interior_tile.transparent is True)
    print()

    print("Checking place_door with type_id='door_stone'...")
    place_door(layer, 5, 0, type_id="door_stone")
    door_tile = layer.tiles[0][5]
    check("Door tile walkable is True", door_tile.walkable is True)
    check("Door tile transparent is True", door_tile.transparent is True)
    print()

    print("=== All checks PASSED ===")


if __name__ == "__main__":
    main()

"""Verification script for the ResourceLoader / TileRegistry pipeline.

Run from project root:
    python3 tests/verify_resource_loader.py
"""

import sys
import os

# Ensure project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SpriteLayer
from map.tile_registry import TileRegistry
from services.resource_loader import ResourceLoader

TILE_FILE = "assets/data/tile_types.json"


def check(description: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}")
    if not condition:
        raise AssertionError(f"Check failed: {description}")


def main():
    print("=== ResourceLoader / TileRegistry Verification ===\n")

    # --- clear registry to start fresh ---
    TileRegistry.clear()

    # --- load tiles ---
    print(f"Loading: {TILE_FILE}")
    ResourceLoader.load_tiles(TILE_FILE)
    print()

    # --- floor_stone ---
    print("Checking floor_stone...")
    floor = TileRegistry.get("floor_stone")
    check("floor_stone exists in registry", floor is not None)
    check("floor_stone.walkable is True", floor.walkable is True)
    check("floor_stone.transparent is True", floor.transparent is True)
    check("floor_stone.occludes_below is False", floor.occludes_below is False)
    check("floor_stone has GROUND sprite", SpriteLayer.GROUND in floor.sprites)
    check("floor_stone GROUND sprite is '.'", floor.sprites[SpriteLayer.GROUND] == ".")
    check("floor_stone sprite key is SpriteLayer enum",
          isinstance(list(floor.sprites.keys())[0], SpriteLayer))
    print()

    # --- wall_stone ---
    print("Checking wall_stone...")
    wall = TileRegistry.get("wall_stone")
    check("wall_stone exists in registry", wall is not None)
    check("wall_stone.walkable is False", wall.walkable is False)
    check("wall_stone.transparent is False", wall.transparent is False)
    check("wall_stone.occludes_below is False", wall.occludes_below is False)
    check("wall_stone has GROUND sprite", SpriteLayer.GROUND in wall.sprites)
    check("wall_stone GROUND sprite is '#'", wall.sprites[SpriteLayer.GROUND] == "#")
    print()

    # --- door_stone ---
    print("Checking door_stone...")
    door = TileRegistry.get("door_stone")
    check("door_stone exists in registry", door is not None)
    check("door_stone.walkable is True", door.walkable is True)
    check("door_stone.transparent is True", door.transparent is True)
    print()

    # --- roof_thatch ---
    print("Checking roof_thatch...")
    roof = TileRegistry.get("roof_thatch")
    check("roof_thatch exists in registry", roof is not None)
    check("roof_thatch.walkable is True", roof.walkable is True)
    check("roof_thatch.transparent is False", roof.transparent is False)
    check("roof_thatch.occludes_below is True", roof.occludes_below is True)
    print()

    # --- general registry checks ---
    print("Checking general registry state...")
    all_ids = TileRegistry.all_ids()
    check("Registry contains at least 4 tile types", len(all_ids) >= 4)
    print()

    # --- error handling: missing file ---
    print("Checking error handling (missing file)...")
    try:
        ResourceLoader.load_tiles("nonexistent_file.json")
        check("FileNotFoundError raised for missing file", False)
    except FileNotFoundError:
        check("FileNotFoundError raised for missing file", True)
    print()

    print("=== All checks PASSED ===")


if __name__ == "__main__":
    main()

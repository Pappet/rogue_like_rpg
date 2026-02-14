"""Verification tests for MapService.load_prefab() and the prefab JSON format.

Tests that:
1. Prefab tiles are stamped onto the MapLayer via set_type(), mutating existing tiles.
2. Tile visibility state is preserved during stamping (proving set_type() is used, not
   Tile construction).
3. Entity spawn points in the prefab are created via EntityFactory.
4. The ox/oy offset is applied correctly for both tiles and entity spawns.
5. FileNotFoundError is raised when the prefab file does not exist.

Run from project root:
    python -m pytest tests/verify_prefab_loading.py -v
"""

import sys
import os

# Ensure project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from map.tile import Tile, VisibilityState
from map.tile_registry import TileRegistry
from map.map_layer import MapLayer
from entities.entity_registry import EntityRegistry
from entities.entity_factory import EntityFactory
from services.map_service import MapService
from services.resource_loader import ResourceLoader
from ecs.world import get_world, reset_world
from ecs.components import Position, Name

TILE_FILE = "assets/data/tile_types.json"
ENTITY_FILE = "assets/data/entities.json"
PREFAB_FILE = "assets/data/prefabs/cottage_interior.json"


def setup_registries():
    """Clear and reload both registries for test isolation."""
    TileRegistry.clear()
    EntityRegistry.clear()
    ResourceLoader.load_tiles(TILE_FILE)
    ResourceLoader.load_entities(ENTITY_FILE)


def make_layer(width: int, height: int, fill_type_id: str = "floor_stone") -> MapLayer:
    """Helper: create a MapLayer filled with a single tile type."""
    tiles = [
        [Tile(type_id=fill_type_id) for _ in range(width)]
        for _ in range(height)
    ]
    return MapLayer(tiles)


def test_load_prefab_stamps_tiles():
    """Prefab tiles are correctly stamped onto the MapLayer at the given offset."""
    setup_registries()
    reset_world()
    world = get_world()

    layer = make_layer(10, 10, "floor_stone")
    map_service = MapService()

    # Stamp at offset (1, 1)
    map_service.load_prefab(world, layer, PREFAB_FILE, ox=1, oy=1)

    # Top-left corner of prefab is wall_stone -> not walkable
    assert not layer.tiles[1][1].walkable, "Tile at prefab offset (0,0) should be wall_stone (not walkable)"

    # Interior of prefab is floor_stone -> walkable
    assert layer.tiles[2][2].walkable, "Tile at prefab offset (1,1) should be floor_stone (walkable)"

    # Tile outside prefab area (row 0, col 0) should be unchanged (floor_stone)
    assert layer.tiles[0][0].walkable, "Tile at (0,0) outside prefab area should remain floor_stone (walkable)"


def test_load_prefab_preserves_visibility():
    """Tile visibility state is preserved during prefab stamping.

    This proves set_type() is used rather than constructing new Tile objects.
    """
    setup_registries()
    reset_world()
    world = get_world()

    layer = make_layer(10, 10, "floor_stone")
    # Mark tile (2,2) as VISIBLE before stamping
    layer.tiles[2][2].visibility_state = VisibilityState.VISIBLE

    map_service = MapService()
    # Stamp at offset (0,0): prefab row 2, col 2 (interior floor_stone) covers (2,2)
    map_service.load_prefab(world, layer, PREFAB_FILE, ox=0, oy=0)

    # Visibility state should survive the set_type() call
    assert layer.tiles[2][2].visibility_state == VisibilityState.VISIBLE, (
        "Visibility state should be preserved after stamping via set_type()"
    )


def test_load_prefab_spawns_entities():
    """Entity spawn points in the prefab are created via EntityFactory at the correct position."""
    setup_registries()
    reset_world()
    world = get_world()

    layer = make_layer(10, 10, "floor_stone")
    map_service = MapService()

    # Cottage prefab has an orc spawn at x=3, y=3 with offset (0, 0)
    map_service.load_prefab(world, layer, PREFAB_FILE, ox=0, oy=0)

    # Find entities with Position and Name
    found = False
    for _, (pos, name) in world.get_components(Position, Name):
        if name.name == "Orc" and pos.x == 3 and pos.y == 3:
            found = True
            break

    assert found, "Expected an Orc entity at position (3, 3) after loading the cottage prefab"


def test_load_prefab_with_offset():
    """Offset is applied to both tile stamps and entity spawns."""
    setup_registries()
    reset_world()
    world = get_world()

    # Use a 20x20 layer so the prefab + offset fits
    layer = make_layer(20, 20, "floor_stone")
    map_service = MapService()

    ox, oy = 5, 5
    map_service.load_prefab(world, layer, PREFAB_FILE, ox=ox, oy=oy)

    # Top-left corner of prefab (0,0) maps to (5,5) -> wall_stone
    assert not layer.tiles[5][5].walkable, (
        "Tile at prefab offset origin (5,5) should be wall_stone (not walkable)"
    )

    # Orc spawn is at x=3, y=3 in prefab -> (5+3, 5+3) = (8, 8)
    found = False
    for _, (pos, name) in world.get_components(Position, Name):
        if name.name == "Orc" and pos.x == 8 and pos.y == 8:
            found = True
            break

    assert found, "Expected an Orc entity at position (8, 8) with ox=5, oy=5 offset"


def test_load_prefab_file_not_found():
    """FileNotFoundError is raised when the prefab file does not exist."""
    setup_registries()
    reset_world()
    world = get_world()

    layer = make_layer(10, 10, "floor_stone")
    map_service = MapService()

    with pytest.raises(FileNotFoundError):
        map_service.load_prefab(world, layer, "nonexistent.json")

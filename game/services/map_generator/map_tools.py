"""Small map utilities that belong to no single generation domain:
terrain scattering, prefab stamping and the plain test map.
"""

import json
import os
import random

from config import SpriteLayer
from game.content.entity_factory import EntityFactory
from game.map.map_container import MapContainer
from game.map.map_generator_utils import get_nearest_walkable_tile
from game.map.map_layer import MapLayer
from game.map.tile import Tile


def apply_terrain_variety(layer: MapLayer, chance: float, type_id_choices: list, rng: random.Random) -> None:
    """
    Adds random terrain variety to a MapLayer by randomly reassigning tile types.

    Args:
        layer:            The MapLayer to vary.
        chance:           Probability (0-1) of replacing each floor tile.
        type_id_choices:  List of registry type_ids to randomly choose from.
        rng:              The generator's run-seeded RNG.
    """
    for y in range(layer.height):
        for x in range(layer.width):
            tile = layer.tiles[y][x]
            # Only apply to walkable ground tiles (floor_stone equivalent).
            if tile.walkable and rng.random() < chance:
                type_id = rng.choice(type_id_choices)
                tile.set_type(type_id)


def create_sample_map(map_service, width: int, height: int, map_id: str | None = None) -> MapContainer:
    """Creates a sample map for testing and optionally registers it."""
    tiles = []
    for y in range(height):
        row = []
        for x in range(width):
            # Determine tile type based on position
            is_border = x == 0 or x == width - 1 or y == 0 or y == height - 1
            is_internal_wall = (x == 10 and 5 < y < 15) or (y == 10 and 5 < x < 15)

            if is_border or is_internal_wall:
                tile = Tile(type_id="wall_stone")
            else:
                tile = Tile(type_id="floor_stone")

            # Add some random decor (preserved as sprite override)
            if x == 5 and y == 5:
                tile.sprites[SpriteLayer.DECOR_BOTTOM] = "T"

            row.append(tile)
        tiles.append(row)

    layer = MapLayer(tiles)
    container = MapContainer([layer])

    if map_id:
        map_service.register_map(map_id, container)

    return container


def load_prefab(world, layer: MapLayer, filepath: str, ox: int = 0, oy: int = 0) -> None:
    """Stamp a prefab JSON file onto an existing MapLayer at an offset.

    The prefab defines a 2D tile grid plus optional entity spawn points.
    Tiles are mutated in-place via set_type(), preserving per-instance
    state such as visibility_state.

    Args:
        world:    The ECS world (used to spawn entities).
        layer:    The MapLayer to stamp tiles onto.
        filepath: Path to the prefab JSON file.
        ox:       X offset for placement on the layer.
        oy:       Y offset for placement on the layer.

    Raises:
        FileNotFoundError: If filepath does not exist.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Prefab file not found: '{filepath}'")

    with open(filepath) as f:
        data = json.load(f)

    tiles_grid = data["tiles"]
    for row_idx, row in enumerate(tiles_grid):
        for col_idx, type_id in enumerate(row):
            tx = ox + col_idx
            ty = oy + row_idx
            if 0 <= ty < layer.height and 0 <= tx < layer.width:
                layer.tiles[ty][tx].set_type(type_id)

    for spawn in data.get("entities", []):
        nx, ny = get_nearest_walkable_tile(layer, ox + spawn["x"], oy + spawn["y"])
        EntityFactory.create(world, spawn["template_id"], nx, ny)

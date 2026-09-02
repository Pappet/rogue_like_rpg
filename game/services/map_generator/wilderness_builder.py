"""The biome-flavored wilderness surrounding a settlement.

Not a world-graph node: entered and left through portals at the settlement
edge. Terrain, features, wildlife and resource nodes all come from
assets/data/biomes.json, drawn from a single per-map RNG.
"""

import json
import random

from config import SpriteLayer
from game.components import MapBound, Name, Portal, Position, Renderable
from game.content.entity_factory import EntityFactory
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.gather_service import create_resource_node
from game.services.map_generator.constants import WILDERNESS_SIZE
from game.services.map_generator.prop_entities import place_light


def wilderness_map_id(settlement_id: str) -> str:
    """Map id of a settlement's surrounding wilderness."""
    return f"{settlement_id} Wilderness"


def wilderness_arrival_pos() -> tuple[int, int]:
    """Where the player enters the wilderness (kept clear of features)."""
    return (WILDERNESS_SIZE // 2, WILDERNESS_SIZE - 3)


def create_wilderness(
    world,
    map_service,
    settlement_id: str,
    biome_id: str,
    return_pos: tuple[int, int],
    seed: int | None = None,
) -> MapContainer:
    """Generate the biome-flavored wilderness surrounding a settlement.

    Not a world-graph node: entered and left through portals at the
    settlement edge. Terrain, features (trees, water) and wildlife all
    come from assets/data/biomes.json. A clearing around the arrival
    spot stays free so the return portal is always reachable.

    Must be called AFTER the settlement maps are frozen — freeze()
    collects every live MapBound entity.
    """
    with open("assets/data/biomes.json") as f:
        biome = json.load(f)[biome_id]
    rng = random.Random(seed)
    size = WILDERNESS_SIZE
    ax, ay = wilderness_arrival_pos()

    tiles = [[Tile(type_id=biome["base"]) for _ in range(size)] for _ in range(size)]
    layer = MapLayer(tiles)
    for y in range(size):
        for x in range(size):
            # Keep a clearing around the arrival/return spot
            if abs(x - ax) <= 2 and abs(y - ay) <= 2:
                continue
            roll = rng.random()
            threshold = 0.0
            placed = False
            for type_id, chance in biome.get("features", []):
                threshold += chance
                if roll < threshold:
                    tiles[y][x].set_type(type_id)
                    placed = True
                    break
            if placed:
                continue
            for type_id, chance in biome.get("patches", []):
                threshold += chance
                if roll < threshold:
                    tiles[y][x].set_type(type_id)
                    break

    # Big trees: 3x3 stamps with a blocking trunk and a walkable,
    # view-blocking canopy ring (count comes from the biome data).
    _stamp_big_trees(tiles, biome.get("big_trees", 0), rng, (ax, ay))

    container = MapContainer([layer], arrival_pos=(ax, ay))
    map_id = wilderness_map_id(settlement_id)
    if map_service.get_map(map_id) is not None:
        raise ValueError(f"Map id '{map_id}' is already registered.")
    map_service.register_map(map_id, container)

    # Return portal one step south of the arrival spot
    world.create_entity(
        MapBound(),
        Position(ax, ay + 1, 0),
        Portal(settlement_id, return_pos[0], return_pos[1], 0, f"Back to {settlement_id}", travel_ticks=10),
        Renderable("&", SpriteLayer.DECOR_BOTTOM.value, (200, 180, 80)),
        Name(f"Path back to {settlement_id}"),
    )

    # A hunter's campfire marks the clearing after dark
    place_light(world, "campfire", ax - 2, ay - 1)

    # Wildlife per the biome's spawn table
    walkable = [
        (x, y)
        for y in range(size)
        for x in range(size)
        if tiles[y][x].walkable and not (abs(x - ax) <= 2 and abs(y - ay) <= 2)
    ]
    rng.shuffle(walkable)
    cursor = 0
    for template_id, count in biome.get("spawns", []):
        for _ in range(count):
            if cursor >= len(walkable):
                break
            x, y = walkable[cursor]
            cursor += 1
            EntityFactory.create(world, template_id, x, y)

    # Harvestable resource nodes scattered per the biome's resource table.
    for kind, count in biome.get("resources", []):
        for _ in range(count):
            if cursor >= len(walkable):
                break
            x, y = walkable[cursor]
            cursor += 1
            create_resource_node(world, kind, x, y, 0)

    container.freeze(world)
    return container


def _stamp_big_trees(tiles: list, count: int, rng: random.Random, clearing: tuple[int, int]) -> None:
    """Stamp up to `count` 3x3 trees onto a wilderness tile grid.

    Each tree is a blocking tree_trunk surrounded by eight tree_canopy
    tiles (walkable, but they block line of sight — forests cast real
    view shadows). Stamps only go onto fully walkable ground, never
    into the arrival clearing, and never overlap each other.
    """
    size = len(tiles)
    ax, ay = clearing
    placed = 0
    attempts = count * 20
    while placed < count and attempts > 0:
        attempts -= 1
        cx = rng.randint(1, size - 2)
        cy = rng.randint(1, size - 2)
        # Keep the arrival/return clearing (and one tile of margin) open
        if abs(cx - ax) <= 3 and abs(cy - ay) <= 3:
            continue
        area = [(cx + dx, cy + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
        if not all(tiles[y][x].walkable and tiles[y][x]._type_id != "tree_canopy" for x, y in area):
            continue
        for x, y in area:
            tiles[y][x].set_type("tree_canopy")
        tiles[cy][cx].set_type("tree_trunk")
        placed += 1

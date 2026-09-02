"""Procedural POI dungeons: rooms and corridors, themed by world.json.

Rooms are carved into solid rock and connected by L-corridors; the monster
pool, hidden cache and resource-node kinds come from the POI's world-graph
entry, each falling back to a generic dungeon default.
"""

import random

import esper

from game.components import Hidden
from game.content.item_factory import ItemFactory
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.gather_service import create_resource_node
from game.services.spawn_service import SpawnService


def create_dungeon(
    world,
    map_service,
    map_id: str,
    width: int = 30,
    height: int = 30,
    seed: int | None = None,
    monster_density: float = 0.025,
    monsters: list[str] | None = None,
    cache: list[str] | None = None,
    resources: list[str] | None = None,
) -> MapContainer:
    """Generate a small procedural dungeon for a POI (ROADMAP Phase F).

    Classic rooms-and-corridors: carve random non-overlapping rooms into
    solid rock, connect consecutive room centers with L-corridors.
    Spawns monsters and places a hidden cache in the last room — the
    secret the Investigate/perception mechanics can uncover.

    ``monsters`` / ``cache`` / ``resources`` theme the place (see the POI
    entries in world.json): the monster pool that guards it, the items in
    its hidden cache, and any resource-node kinds to seed through its rooms
    (e.g. ore and coal veins in the Abandoned Mine). Each falls back to the
    generic dungeon defaults when empty.

    The map is registered and left frozen (like create_scenario);
    arrival_pos is the center of the first room.
    """
    cache = cache or ["steel_sword", "health_potion"]

    rng = random.Random(seed)
    tiles = [[Tile(type_id="wall_stone") for _ in range(width)] for _ in range(height)]
    layer = MapLayer(tiles)

    # 1. Carve rooms
    rooms: list[tuple[int, int, int, int]] = []  # (x, y, w, h)
    for _ in range(40):
        if len(rooms) >= 7:
            break
        rw, rh = rng.randint(4, 8), rng.randint(4, 7)
        rx, ry = rng.randint(1, width - rw - 2), rng.randint(1, height - rh - 2)
        if any(
            rx < ox + ow + 1 and rx + rw + 1 > ox and ry < oy + oh + 1 and ry + rh + 1 > oy for ox, oy, ow, oh in rooms
        ):
            continue
        rooms.append((rx, ry, rw, rh))
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                tiles[y][x].set_type("floor_stone")

    # 2. Connect consecutive rooms with L-corridors
    def center(room):
        rx, ry, rw, rh = room
        return rx + rw // 2, ry + rh // 2

    for a, b in zip(rooms, rooms[1:], strict=False):
        ax, ay = center(a)
        bx, by = center(b)
        for x in range(min(ax, bx), max(ax, bx) + 1):
            tiles[ay][x].set_type("floor_stone")
        for y in range(min(ay, by), max(ay, by) + 1):
            tiles[y][bx].set_type("floor_stone")

    container = MapContainer([layer], arrival_pos=center(rooms[0]))
    if map_service.get_map(map_id) is not None:
        raise ValueError(f"Map id '{map_id}' is already registered.")
    map_service.register_map(map_id, container)

    # 3. Monsters guard the place (themed pool when the POI defines one)
    SpawnService.spawn_monsters(world, container, density=monster_density, monsters=monsters)

    # 3b. Resource nodes seeded through the middle rooms (themed POIs only,
    # e.g. ore/coal/gem veins in the Abandoned Mine). Each goes at a room
    # centre so its bump neighbours stay clear.
    if resources and len(rooms) > 2:
        for i, kind in enumerate(resources):
            rx, ry = center(rooms[1 + (i % (len(rooms) - 2))])
            create_resource_node(world, kind, rx, ry, 0)

    # 4. Hidden cache in the last room (Phase F secret)
    cx, cy = center(rooms[-1])
    for template_id in cache:
        item = ItemFactory.create_on_ground(world, template_id, cx, cy, 0)
        esper.add_component(item, Hidden())

    container.freeze(world)
    return container

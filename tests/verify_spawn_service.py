"""Spawn collision rules: monsters must never appear on an occupied tile.

`SpawnService.spawn_monsters` used to pick spawn tiles purely by
``tile.walkable`` — a tile already holding a Blocker, an NPC or any other
positioned entity was still considered free, so a monster could appear on
a resource node, inside a doorway blocker or on top of another NPC.

These tests pin the corrected rule: a spawn tile must be walkable *and*
free of entities on that layer. ``test_spawn_never_lands_on_occupied_tile``
fails against the old implementation (it demonstrates the bug); the rest
pin the fixed behavior.

Spawned monsters are identified by entity id (everything the test did not
place itself), since monster templates carry a ``Blocker`` themselves.
"""

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from game.components import Blocker, Position
from game.content.resource_loader import ResourceLoader
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.spawn_service import SpawnService


def _load_content():
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")


def _container(width, height):
    """A single-layer map, fully walkable floor."""
    tiles = [[Tile(type_id="floor_stone") for _ in range(width)] for _ in range(height)]
    return MapContainer([MapLayer(tiles)])


def _place_blockers(container, predicate):
    """Place a Blocker entity on every tile matching predicate; return their ids."""
    layer = container.layers[0]
    ids = set()
    for y in range(layer.height):
        for x in range(layer.width):
            if predicate(x, y):
                ids.add(esper.create_entity(Position(x, y, 0), Blocker()))
    return ids


def _spawned_positions(placed_ids):
    """Positions of entities the test did not place (i.e. the monsters)."""
    return [pos for ent, pos in esper.get_component(Position) if ent not in placed_ids]


# ---------------------------------------------------------------------------
# The bug: spawning onto occupied tiles
# ---------------------------------------------------------------------------


def test_spawn_never_lands_on_occupied_tile():
    """Every walkable tile holds a blocker -> a spawn must skip them all.

    With the old walkable-only check this spawned monsters *on top of*
    the blockers; the fix filters occupied tiles out of the candidate set.
    """
    _load_content()
    random.seed(7)
    container = _container(8, 8)
    placed = _place_blockers(container, lambda x, y: True)

    SpawnService.spawn_monsters(esper, container, density=0.1)

    # Nothing new may have appeared: there was no free tile to spawn on.
    assert _spawned_positions(placed) == [], "Spawn ignored entity occupancy — new entities on occupied tiles"


def test_spawned_monsters_never_share_a_tile_with_another_entity():
    """A crowded map: monsters may only stand on genuinely free tiles."""
    _load_content()
    random.seed(11)
    container = _container(10, 10)
    placed = _place_blockers(container, lambda x, y: (x + y) % 2 == 0)

    SpawnService.spawn_monsters(esper, container, density=0.5)

    monsters = [(pos.x, pos.y, pos.layer) for pos in _spawned_positions(placed)]
    assert len(monsters) > 0, "Spawn placed nothing although free tiles existed"
    assert all(m not in {(x, y, 0) for y in range(10) for x in range(10) if (x + y) % 2 == 0} for m in monsters), (
        "Monster spawned on an occupied tile"
    )
    assert len(monsters) == len(set(monsters)), "Two entities share a tile"


def test_spawn_counts_only_free_tiles():
    """Density targets a count, but occupancy caps how many can be placed.

    36 tiles with a checkerboard of blockers: the old code spawned its full
    density target regardless, stacking monsters onto the blockers. The fixed
    code may use only the tiles that are genuinely free, and stacks nothing.
    """
    _load_content()
    random.seed(3)
    container = _container(6, 6)
    blocked = {(x, y) for y in range(6) for x in range(6) if (x + y) % 2 == 0}
    placed = _place_blockers(container, lambda x, y: (x, y) in blocked)
    # (1, 1) is reserved as the player start, but is already blocked here.
    free = {(x, y) for y in range(6) for x in range(6)} - blocked - {(1, 1)}

    SpawnService.spawn_monsters(esper, container, density=0.5)

    monsters = [(pos.x, pos.y, pos.layer) for pos in _spawned_positions(placed)]
    assert 0 < len(monsters) <= len(free)
    assert all((mx, my) in free for mx, my, _ in monsters), "Monster on an occupied tile"
    assert len(monsters) == len(set(monsters)), "Two entities share a tile"

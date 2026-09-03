"""Dressing harvestable resource nodes into real map objects.

A bare node glyph reads as a floating symbol; painting terrain around it turns
it into a grain field, a rocky outcrop or a pond. Blocking decor keeps the
node's four orthogonal neighbours clear so it stays bump-reachable.
"""

import random

from game.map.map_layer import MapLayer
from game.services.map_generator.constants import DECOR_PAINTABLE, RESOURCE_DECOR


def decorate_resource(layer: MapLayer, kind: str, nx: int, ny: int, rng: random.Random) -> None:
    """Dress a resource node into a field / rocky outcrop / pond around (nx, ny)."""
    spec = RESOURCE_DECOR.get(kind)
    if spec is None:
        return

    def paint(x: int, y: int) -> None:
        if not (0 <= y < layer.height and 0 <= x < layer.width):
            return
        tile = layer.tiles[y][x]
        if tile.type_id in DECOR_PAINTABLE:
            tile.set_type(spec["tile"])

    if spec["fill_node"]:
        paint(nx, ny)

    r = spec["radius"]
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx == 0 and dy == 0:
                continue
            # Keep the four orthogonal neighbours of a blocking patch clear so
            # there is always a tile to stand on and bump the node from.
            if spec["blocking"] and abs(dx) + abs(dy) == 1:
                continue
            if rng.random() < spec["chance"]:
                paint(nx + dx, ny + dy)

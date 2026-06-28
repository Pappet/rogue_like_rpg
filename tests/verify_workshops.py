"""Workshop buildings, open shelters and dressed resource nodes.

Covers the integration of crafting stations into dedicated structures:
- enterable workshops carry their station tile inside the interior map,
- open shelters wrap a station under a cutaway roof on the layer above,
- resource nodes are dressed into fields / rocky outcrops / ponds while
  staying reachable to bump.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pytest

from game.components import Position, ResourceNode
from game.content.resource_loader import ResourceLoader
from game.map.tile import Tile
from game.services.map_generator import RESOURCE_DECOR, STATION_TILES, MapGenerator
from game.services.map_service import MapService

SCENARIOS = [
    ("village", "Village"),
    ("brackenfen", "Brackenfen"),
    ("eastmoor", "Eastmoor"),
    ("foxhollow", "Foxhollow"),
    ("saltmarsh", "Saltmarsh"),
    ("timberfall", "Timberfall"),
]


@pytest.fixture(autouse=True)
def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_items("assets/data/items.json")


def _build(scenario: str, map_id: str):
    ms = MapService()
    gen = MapGenerator(ms, seed=99)
    container = gen.create_scenario(esper, f"assets/data/scenarios/{scenario}.json", map_id=map_id)
    return ms, container


# --- Roof tile property -------------------------------------------------------


def test_roof_tile_flag():
    assert Tile(type_id="roof_plank").is_roof is True
    assert Tile(type_id="floor_stone").is_roof is False


# --- Open shelters ------------------------------------------------------------


def test_shelter_has_station_under_a_cutaway_roof():
    _, container = _build("village", "Village")
    ground, roof = container.layers[0], container.layers[1]

    # The Village oven shelter sits at [33, 23] size 4x4 -> centre station (35, 25).
    station = ground.tiles[25][35]
    assert station.crafting_station == "oven"
    assert station.walkable is False
    # A roof covers the whole footprint on the layer above.
    assert roof.tiles[25][35].is_roof is True
    assert roof.tiles[23][33].is_roof is True  # corner of the footprint


def test_roof_cutaway_reveals_only_when_under():
    _, container = _build("village", "Village")
    # Standing under the oven shelter peels the whole 4x4 roof footprint.
    under = container.roof_cutaway(34, 24, 0)
    assert len(under) == 16
    assert (35, 25) in under
    # Standing out on the street reveals nothing.
    assert container.roof_cutaway(20, 38, 0) == set()


def test_every_shelter_station_is_reachable():
    """A player must be able to stand next to each shelter station and bump it."""
    for scenario, map_id in SCENARIOS:
        ms, container = _build(scenario, map_id)
        ground = container.layers[0]
        for y in range(container.height):
            for x in range(container.width):
                if not ground.tiles[y][x].crafting_station:
                    continue
                neighbours = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
                assert any(container.is_walkable(nx, ny, 0) for nx, ny in neighbours), (
                    f"{map_id}: exterior station at {(x, y)} is walled in"
                )


# --- Enterable workshops ------------------------------------------------------


def test_enterable_workshop_places_station_inside_interior():
    # The Mill is an enterable, multi-floor building; its station lives indoors.
    ms, _ = _build("village", "Village")
    interior = ms.get_map("Village Mill")
    assert interior is not None
    assert len(interior.layers) == 2, "an enterable workshop should have multiple floors"
    stations = [
        interior.layers[0].tiles[y][x].crafting_station
        for y in range(interior.height)
        for x in range(interior.width)
        if interior.layers[0].tiles[y][x].crafting_station
    ]
    assert stations == ["mill"]


# --- Dressed resource nodes ---------------------------------------------------


def test_resource_nodes_are_dressed_and_reachable():
    for scenario, map_id in SCENARIOS:
        ms, container = _build(scenario, map_id)
        ground = container.layers[0]

        for components in container.frozen_entities:
            node = next((c for c in components if isinstance(c, ResourceNode)), None)
            pos = next((c for c in components if isinstance(c, Position)), None)
            if node is None or pos is None:
                continue

            # Whatever kind it is, the node must still be bump-reachable.
            neighbours = [(pos.x + 1, pos.y), (pos.x - 1, pos.y), (pos.x, pos.y + 1), (pos.x, pos.y - 1)]
            assert any(container.is_walkable(nx, ny, 0) for nx, ny in neighbours), (
                f"{map_id}: {node.item} node at {(pos.x, pos.y)} is unreachable"
            )


def test_grain_field_paints_crop_tiles_around_node():
    ms, container = _build("village", "Village")
    ground = container.layers[0]

    crop_tiles = sum(1 for row in ground.tiles for t in row if t.type_id == "crop_field")
    assert crop_tiles > 0, "grain fields should leave crop terrain behind"


def test_decor_catalogue_uses_real_tiles():
    for kind, spec in RESOURCE_DECOR.items():
        # Tile() raises if the type id is unknown in the registry.
        Tile(type_id=spec["tile"])


def test_station_types_all_have_tiles():
    # Every station referenced by a shelter/workshop maps to a real tile.
    for station_type, tile_id in STATION_TILES.items():
        assert Tile(type_id=tile_id).crafting_station == station_type

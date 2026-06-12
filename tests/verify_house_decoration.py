"""Tests for house exterior shells (roof/door/windows) and styled interiors."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from game.components import Portal, Position
from game.content.resource_loader import ResourceLoader
from game.services.map_generator import MapGenerator
from game.services.map_service import MapService


def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_items("assets/data/items.json")


def _build_village():
    map_service = MapService()
    MapGenerator(map_service).create_scenario(esper, "assets/data/scenarios/village.json")
    return map_service


def _type_ids(container, z=0):
    return {t._type_id for row in container.layers[z].tiles for t in row}


def _count(container, type_id, z=0):
    return sum(1 for row in container.layers[z].tiles for t in row if t._type_id == type_id)


# ---------------------------------------------------------------------------
# Exterior: roof fill, walls, door and windows on the village map
# ---------------------------------------------------------------------------


def test_house_exteriors_have_roof_door_and_windows():
    _load_content()
    map_service = _build_village()
    village = map_service.get_map("Village")
    tiles = village.layers[0].tiles

    ids = _type_ids(village)
    assert "roof_thatch" in ids, "house footprints should be filled with thatch"
    assert "door_wood" in ids, "every house needs a visible front door"
    assert "wall_window" in ids, "front walls should have windows"

    # Cottage at v_pos (5,5), v_size (6,6): door mid-south, roof inside walls
    assert tiles[10][8]._type_id == "door_wood"
    assert tiles[7][7]._type_id == "roof_thatch"
    assert not tiles[7][7].walkable, "nobody walks around inside the shell"
    assert tiles[5][5]._type_id == "wall_wood", "the cottage is a wooden house"


def test_house_footprints_start_shrouded():
    """Roofs are visible from the street: footprints start SHROUDED, not black."""
    from game.map.tile import VisibilityState

    _load_content()
    map_service = _build_village()
    tiles = map_service.get_map("Village").layers[0].tiles

    # Cottage footprint (5,5)-(10,10) including the roof interior
    for y in range(5, 11):
        for x in range(5, 11):
            assert tiles[y][x].visibility_state == VisibilityState.SHROUDED
    # Ordinary ground stays unexplored
    assert tiles[20][20].visibility_state == VisibilityState.UNEXPLORED


def test_enter_portal_sits_on_the_doorstep():
    _load_content()
    map_service = _build_village()
    village = map_service.get_map("Village")

    doors = []
    for comps in village.frozen_entities:
        portal = next((c for c in comps if isinstance(c, Portal)), None)
        pos = next((c for c in comps if isinstance(c, Position)), None)
        if portal and pos and portal.target_map_id in ("Cottage", "Tavern", "Shop"):
            doors.append((portal.target_map_id, pos))
    assert len(doors) == 3

    tiles = village.layers[0].tiles
    for target, pos in doors:
        tile = tiles[pos.y][pos.x]
        assert tile._type_id == "door_wood", f"portal to {target} must stand on the door tile"
        assert tile.walkable
        # The tile in front of the door (return-portal target) stays open ground
        assert tiles[pos.y + 1][pos.x].walkable


# ---------------------------------------------------------------------------
# Interiors: wooden floors, windows and style-driven furniture
# ---------------------------------------------------------------------------


def test_home_interior_is_furnished():
    _load_content()
    map_service = _build_village()
    cottage = map_service.get_map("Cottage")

    ids = _type_ids(cottage)
    assert "floor_wood" in ids, "homes have wooden floorboards"
    assert "wall_window" in ids
    assert "furniture_bed" in ids
    assert "furniture_table" in ids
    assert "fireplace" in ids


def test_tavern_has_counter_and_guest_beds_upstairs():
    _load_content()
    map_service = _build_village()
    tavern = map_service.get_map("Tavern")

    assert "furniture_counter" in _type_ids(tavern, z=0)
    assert "furniture_table" in _type_ids(tavern, z=0)
    assert _count(tavern, "furniture_bed", z=1) >= 2, "the tavern rents out beds upstairs"


def test_shop_has_counter_and_shelves():
    _load_content()
    map_service = _build_village()
    shop = map_service.get_map("Shop")

    ids = _type_ids(shop)
    assert "furniture_counter" in ids
    assert "furniture_shelf" in ids
    assert shop.layers[0].tiles[0][0]._type_id == "wall_stone", "shops are stone buildings"


def test_furniture_never_blocks_stairs_or_entry():
    _load_content()
    map_service = _build_village()

    for house_id in ("Cottage", "Tavern", "Shop"):
        container = map_service.get_map(house_id)
        w = container.layers[0].width
        h = container.layers[0].height
        tiles0 = container.layers[0].tiles
        # Entry tile (return portal target) and the doorway stay walkable
        assert tiles0[h - 2][w // 2].walkable, f"{house_id}: entry tile blocked"
        assert tiles0[h - 1][w // 2]._type_id == "door_wood", f"{house_id}: missing interior door"
        # Stair corners stay free on every floor
        for z in range(len(container.layers)):
            for sx, sy in ((w - 2, 2), (2, 2)):
                assert container.layers[z].tiles[sy][sx].walkable, f"{house_id} z{z}: stairs at ({sx},{sy}) blocked"

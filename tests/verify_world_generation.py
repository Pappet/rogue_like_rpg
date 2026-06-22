"""Tests for multi-settlement world generation (ROADMAP Phase A2)."""

import esper
import pytest

from game.content.resource_loader import ResourceLoader
from game.services.map_generator import MapGenerator
from game.services.map_service import MapService
from game.services.world_graph_service import WorldGraphService

WORLD_FILE = "assets/data/world.json"


@pytest.fixture(autouse=True)
def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_items("assets/data/items.json")


def _build_world():
    map_service = MapService()
    graph = WorldGraphService.from_file(WORLD_FILE)
    MapGenerator(map_service).create_world(esper, graph)
    return map_service, graph


def test_every_settlement_gets_a_map():
    map_service, graph = _build_world()
    for location in graph.locations.values():
        if location.type == "settlement":
            assert map_service.get_map(location.id) is not None, f"settlement '{location.id}' has no generated map"


def test_start_location_is_active_and_thawed():
    map_service, graph = _build_world()
    assert map_service.active_map_id == graph.start_location_id
    assert map_service.get_active_map().frozen_entities == []


def test_other_settlements_are_frozen():
    map_service, graph = _build_world()
    for location in graph.locations.values():
        if location.type == "settlement" and location.id != graph.start_location_id:
            container = map_service.get_map(location.id)
            assert len(container.frozen_entities) >= 1, (
                f"non-active settlement '{location.id}' should hold frozen entities"
            )


def test_settlements_have_arrival_pos_on_walkable_tile():
    map_service, graph = _build_world()
    for location in graph.locations.values():
        if location.type != "settlement":
            continue
        container = map_service.get_map(location.id)
        assert container.arrival_pos is not None, f"'{location.id}' lacks arrival_pos"
        ax, ay = container.arrival_pos
        assert container.is_walkable(ax, ay, 0), (
            f"arrival_pos {container.arrival_pos} of '{location.id}' is not walkable"
        )


def test_structure_interiors_registered_with_return_portals():
    map_service, _ = _build_world()
    # Spot-check one interior per settlement
    for interior_id in ("Tavern", "Eastmoor Inn", "Brackenfen Trading Post"):
        container = map_service.get_map(interior_id)
        assert container is not None, f"interior map '{interior_id}' missing"
        assert len(container.frozen_entities) >= 1, f"'{interior_id}' has no frozen entities"


def test_duplicate_map_ids_rejected():
    map_service = MapService()
    generator = MapGenerator(map_service)
    generator.create_scenario(esper, "assets/data/scenarios/village.json")
    with pytest.raises(ValueError):
        generator.create_scenario(esper, "assets/data/scenarios/village.json")


def test_poi_dungeons_use_their_themed_monsters_and_caches():
    """Each POI draws from its own monster pool and hides its own cache,
    instead of every dungeon sharing the generic orc/goblin/troll + steel sword."""
    from game.components import Hidden, Name, ResourceNode, TemplateId

    map_service, _ = _build_world()

    def contents(map_id):
        container = map_service.get_map(map_id)
        monsters, cache, nodes = set(), set(), set()
        for comps in container.frozen_entities:
            if any(isinstance(c, ResourceNode) for c in comps):
                nodes.add(next(c.item for c in comps if isinstance(c, ResourceNode)))
            elif any(isinstance(c, Hidden) for c in comps):
                cache.add(next((c.name for c in comps if isinstance(c, Name)), None))
            elif tid := next((c.id for c in comps if isinstance(c, TemplateId)), None):
                monsters.add(tid)
        return monsters, cache, nodes

    crypt_m, crypt_c, _ = contents("Sunken Crypt")
    assert "skeleton" in crypt_m, "the crypt should be full of skeletons"
    assert "orc" not in crypt_m and "troll" not in crypt_m

    camp_m, _, _ = contents("Bandit Camp")
    assert {"bandit", "bandit_leader"} & camp_m, "the bandit camp should hold bandits"

    # The mine actually contains mineable veins.
    _, _, mine_nodes = contents("Abandoned Mine")
    assert {"iron_ore", "coal", "gemstone"} & mine_nodes, "the mine should have ore to dig"

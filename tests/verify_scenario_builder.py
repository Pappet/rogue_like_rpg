"""Tests for the individual scenario build phases.

create_scenario used to be one ~195-line method; it is now an ordered sequence
of named phases in game/services/map_generator/scenario_builder.py. These tests
exercise the phases directly, which the monolith did not allow.
"""

import esper
import pytest

from game.components import ResourceNode
from game.content.resource_loader import ResourceLoader
from game.services.gather_service import RESOURCE_NODES
from game.services.map_generator import MapGenerator, scenario_builder
from game.services.map_service import MapService


@pytest.fixture(autouse=True)
def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_items("assets/data/items.json")


def _gen():
    map_service = MapService()
    return MapGenerator(map_service, seed=99), map_service


def _config(**overrides):
    config = {
        "id": "Testville",
        "dimensions": {"width": 20, "height": 20},
        "base_layer": "floor_grass",
        "arrival_pos": [3, 4],
    }
    config.update(overrides)
    return config


# ---------------------------------------------------------------------------
# Phase 1 — _build_exterior
# ---------------------------------------------------------------------------


def test_build_exterior_registers_three_sized_layers():
    gen, map_service = _gen()
    container, layers = scenario_builder._build_exterior(gen, _config(), "Testville")

    assert map_service.get_map("Testville") is container
    assert len(layers) == 3
    assert (layers[0].width, layers[0].height) == (20, 20)
    assert container.arrival_pos == (3, 4)
    assert layers[0].tiles[0][0].type_id == "floor_grass"


def test_build_exterior_rejects_a_duplicate_map_id():
    gen, _ = _gen()
    scenario_builder._build_exterior(gen, _config(), "Testville")

    with pytest.raises(ValueError, match="already registered"):
        scenario_builder._build_exterior(gen, _config(), "Testville")


# ---------------------------------------------------------------------------
# Phase 3 — _stamp_features
# ---------------------------------------------------------------------------


def test_stamp_features_places_stations_and_harvestable_nodes():
    gen, _ = _gen()
    _, layers = scenario_builder._build_exterior(gen, _config(), "Testville")

    config = _config(
        stations=[{"type": "mill", "pos": [5, 5]}],
        resources=[{"kind": "grain_field", "pos": [10, 10]}],
    )
    scenario_builder._stamp_features(gen, esper, config, layers)

    assert layers[0].tiles[5][5].type_id == "station_mill"

    nodes = [node for _ent, node in esper.get_component(ResourceNode)]
    assert [n.item for n in nodes] == [RESOURCE_NODES["grain_field"][0]]
    # The node is dressed into a real field rather than left as a lone glyph.
    assert layers[0].tiles[10][10].type_id == "crop_field"

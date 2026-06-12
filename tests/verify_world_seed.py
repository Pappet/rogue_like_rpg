"""Run-seed & per-run world variation tests (ROADMAP Phase G1).

The same world seed must reproduce the same world (wilderness layout,
economy starting position); different seeds must produce different runs.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import random

import esper

from core.rng import derive_seed
from game.content.resource_loader import ResourceLoader
from game.services.economy_service import EconomyService
from game.services.map_generator import MapGenerator, wilderness_map_id
from game.services.map_service import MapService


def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_items("assets/data/items.json")


def _terrain_grid(map_service, map_id):
    container = map_service.get_map(map_id)
    return [[t._type_id for t in row] for row in container.layers[0].tiles]


def _build_village(seed):
    map_service = MapService()
    MapGenerator(map_service, seed=seed).create_scenario(esper, "assets/data/scenarios/village.json")
    return map_service


# ---------------------------------------------------------------------------
# Seed derivation
# ---------------------------------------------------------------------------


def test_derive_seed_is_stable_and_label_sensitive():
    assert derive_seed(42, "maps") == derive_seed(42, "maps")
    assert derive_seed(42, "maps") != derive_seed(42, "chronicle")
    assert derive_seed(42, "maps") != derive_seed(43, "maps")
    assert 0 <= derive_seed(42, "maps") < 2**31


# ---------------------------------------------------------------------------
# Map generation determinism
# ---------------------------------------------------------------------------


def test_same_seed_reproduces_settlement_and_wilderness():
    _load_content()
    a = _build_village(seed=1234)
    b = _build_village(seed=1234)

    wild_id = wilderness_map_id("Village")
    assert _terrain_grid(a, wild_id) == _terrain_grid(b, wild_id)
    assert _terrain_grid(a, "Village") == _terrain_grid(b, "Village")


def test_different_seeds_vary_the_wilderness():
    _load_content()
    a = _build_village(seed=1)
    b = _build_village(seed=2)
    assert _terrain_grid(a, wilderness_map_id("Village")) != _terrain_grid(b, wilderness_map_id("Village"))


def test_dungeons_derive_from_the_world_seed():
    _load_content()
    grids = []
    for _ in range(2):
        map_service = MapService()
        gen = MapGenerator(map_service, seed=777)
        gen.create_dungeon(esper, "Old Ruins", seed=gen._map_seed("Old Ruins"))
        grids.append(_terrain_grid(map_service, "Old Ruins"))
    assert grids[0] == grids[1]


# ---------------------------------------------------------------------------
# Economy variation
# ---------------------------------------------------------------------------


def _economy_with_data():
    economy = EconomyService()
    economy.stocks = {"Village": {"health_potion": 5.0, "venison": 2.0}}
    economy.rates_per_day = {"Village": {"health_potion": 2.0, "venison": -1.5}}
    return economy


def test_economy_variation_is_deterministic_per_seed():
    a = _economy_with_data()
    a.apply_variation(random.Random(99))
    b = _economy_with_data()
    b.apply_variation(random.Random(99))
    assert a.stocks == b.stocks
    assert a.rates_per_day == b.rates_per_day


def test_economy_variation_differs_between_seeds_and_keeps_signs():
    a = _economy_with_data()
    a.apply_variation(random.Random(1))
    b = _economy_with_data()
    b.apply_variation(random.Random(2))
    assert a.stocks != b.stocks or a.rates_per_day != b.rates_per_day
    # A producer stays a producer, a consumer stays a consumer
    assert a.rates_per_day["Village"]["health_potion"] > 0
    assert a.rates_per_day["Village"]["venison"] < 0

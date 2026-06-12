"""Tests for placed light props (torches/lanterns/campfires) and their
night-only visibility reveal."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from config import TICKS_PER_HOUR
from core.world_clock_service import WorldClockService
from game.components import LightSource, Name, Position
from game.content.resource_loader import ResourceLoader
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile, VisibilityState
from game.services.map_generator import MapGenerator
from game.services.map_service import MapService
from game.systems.turn_system import TurnSystem
from game.systems.visibility_system import VisibilitySystem

NOON = 12 * TICKS_PER_HOUR
MIDNIGHT = 0


def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_items("assets/data/items.json")


# ---------------------------------------------------------------------------
# Night-only reveal through the VisibilitySystem
# ---------------------------------------------------------------------------


def _visibility_setup(clock):
    _load_content()
    tiles = [[Tile(type_id="floor_grass") for _ in range(20)] for _ in range(20)]
    container = MapContainer([MapLayer(tiles)])
    system = VisibilitySystem(TurnSystem(clock), clock)
    system.set_map(container)
    # A torch far away from any player vision
    esper.create_entity(Position(10, 10, 0), LightSource(radius=3, night_only=True))
    return container, system


def test_night_light_reveals_surroundings_at_night():
    clock = WorldClockService(total_ticks=MIDNIGHT)
    container, system = _visibility_setup(clock)

    system.process()
    assert container.get_tile(10, 10, 0).visibility_state == VisibilityState.VISIBLE
    assert container.get_tile(12, 10, 0).visibility_state == VisibilityState.VISIBLE


def test_night_light_is_dark_during_the_day():
    clock = WorldClockService(total_ticks=NOON)
    container, system = _visibility_setup(clock)

    system.process()
    assert container.get_tile(10, 10, 0).visibility_state == VisibilityState.UNEXPLORED


def test_always_on_light_reveals_during_the_day():
    clock = WorldClockService(total_ticks=NOON)
    container, system = _visibility_setup(clock)
    esper.create_entity(Position(3, 3, 0), LightSource(radius=2, night_only=False))

    system.process()
    assert container.get_tile(3, 3, 0).visibility_state == VisibilityState.VISIBLE


# ---------------------------------------------------------------------------
# Generator placement
# ---------------------------------------------------------------------------


def _frozen_lights(container):
    lights = []
    for comps in container.frozen_entities:
        light = next((c for c in comps if isinstance(c, LightSource)), None)
        name = next((c for c in comps if isinstance(c, Name)), None)
        if light:
            lights.append((name.name if name else "?", light))
    return lights


def test_village_has_torches_and_a_campfire():
    _load_content()
    map_service = MapService()
    MapGenerator(map_service).create_scenario(esper, "assets/data/scenarios/village.json")

    lights = _frozen_lights(map_service.get_map("Village"))
    names = [n for n, _l in lights]
    # One torch per house door + two at the arrival road + the village campfire
    assert names.count("Torch") >= 5
    assert "Campfire" in names
    assert all(light.night_only for _n, light in lights)


def test_house_interiors_have_a_lantern():
    _load_content()
    map_service = MapService()
    MapGenerator(map_service).create_scenario(esper, "assets/data/scenarios/village.json")

    for house_id in ("Cottage", "Tavern", "Shop"):
        names = [n for n, _l in _frozen_lights(map_service.get_map(house_id))]
        assert "Lantern" in names, f"{house_id} should be lit at night"


def test_wilderness_clearing_has_a_campfire():
    _load_content()
    map_service = MapService()
    MapGenerator(map_service).create_scenario(esper, "assets/data/scenarios/village.json")

    names = [n for n, _l in _frozen_lights(map_service.get_map("Village Wilderness"))]
    assert "Campfire" in names


# ---------------------------------------------------------------------------
# Glow rendering
# ---------------------------------------------------------------------------


def test_light_glow_brightens_the_surface():
    pygame.init()
    from core.camera import Camera
    from game.services.render_service import RenderService

    service = RenderService()
    surface = pygame.Surface((320, 320))
    surface.fill((10, 10, 30))
    camera = Camera(320, 320)

    service.render_light_glow(surface, camera, [(5, 5, 3)], strength=1.0)

    sx, sy = camera.tile_to_screen(5, 5)
    center = surface.get_at((sx + 8, sy + 8))
    assert center.r > 10 and center.g > 10, "glow must additively brighten the center"
    corner = surface.get_at((0, 0))
    assert (corner.r, corner.g, corner.b) == (10, 10, 30), "glow must stay local"


def test_no_glow_at_zero_strength():
    pygame.init()
    from core.camera import Camera
    from game.services.render_service import RenderService

    service = RenderService()
    surface = pygame.Surface((320, 320))
    surface.fill((10, 10, 30))

    service.render_light_glow(surface, Camera(320, 320), [(5, 5, 3)], strength=0.0)
    sx, sy = Camera(320, 320).tile_to_screen(5, 5)
    assert surface.get_at((sx + 8, sy + 8)) == (10, 10, 30, 255)

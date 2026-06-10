"""Composition root: builds the complete GameContext exactly once.

All content loading, service construction and system wiring happens here.
Nothing else in the codebase should construct services or systems.
"""

import esper

from components.camera import Camera
from config import HEADER_HEIGHT, LOG_HEIGHT, SCREEN_HEIGHT, SCREEN_WIDTH, SIDEBAR_WIDTH
from game_context import GameContext
from services.dialogue_service import DialogueService
from services.input_manager import InputManager
from services.map_generator import MapGenerator
from services.map_service import MapService
from services.render_service import RenderService
from services.resource_loader import ResourceLoader
from services.system_initializer import build_systems, register_processors
from services.world_clock_service import WorldClockService
from ui.stack_manager import UIStack

DATA_DIR = "assets/data"


def load_content() -> None:
    """Load all JSON game content into the registries."""
    ResourceLoader.load_schedules(f"{DATA_DIR}/schedules.json")
    ResourceLoader.load_tiles(f"{DATA_DIR}/tile_types.json")
    ResourceLoader.load_entities(f"{DATA_DIR}/entities.json")
    ResourceLoader.load_items(f"{DATA_DIR}/items.json")
    DialogueService.load(f"{DATA_DIR}/dialogues.json")


def build_game_context() -> GameContext:
    """Load content, create services and systems, generate the start map."""
    load_content()

    map_service = MapService()
    world_clock = WorldClockService()

    # Viewport is the area not covered by UI header and log
    viewport_width = SCREEN_WIDTH - SIDEBAR_WIDTH
    viewport_height = SCREEN_HEIGHT - HEADER_HEIGHT - LOG_HEIGHT
    camera = Camera(viewport_width, viewport_height, 0, HEADER_HEIGHT)

    MapGenerator(map_service).create_village_scenario(esper)

    systems = build_systems(world_clock, map_service.get_active_map())
    register_processors(systems)

    return GameContext(
        map_service=map_service,
        render_service=RenderService(),
        world_clock=world_clock,
        input_manager=InputManager(),
        ui_stack=UIStack(),
        camera=camera,
        systems=systems,
    )

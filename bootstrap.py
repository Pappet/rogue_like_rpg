"""Composition root: builds the complete GameContext exactly once.

All content loading, service construction and system wiring happens here.
Nothing else in the codebase should construct services or systems.
"""

import esper

from config import HEADER_HEIGHT, LOG_HEIGHT, SCREEN_HEIGHT, SCREEN_WIDTH, SIDEBAR_WIDTH
from core.camera import Camera
from core.input_manager import InputManager
from core.ui.stack_manager import UIStack
from core.world_clock_service import WorldClockService
from game.content.content_database import default_content
from game.services.map_generator import MapGenerator
from game.services.map_service import MapService
from game.services.render_service import RenderService
from game.services.system_initializer import build_systems, register_processors
from game_context import GameContext

DATA_DIR = "assets/data"


def build_game_context() -> GameContext:
    """Load content, create services and systems, generate the start map."""
    content = default_content.load(DATA_DIR)

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
        content=content,
    )

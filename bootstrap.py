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
from game.services.economy_service import EconomyService
from game.services.map_generator import MapGenerator
from game.services.map_service import MapService
from game.services.quest_service import QuestService
from game.services.render_service import RenderService
from game.services.reputation_service import ReputationService
from game.services.rumor_service import RumorService
from game.services.system_initializer import build_systems, register_processors
from game.services.world_chronicle_service import WorldChronicleService
from game.services.world_graph_service import WorldGraphService
from game_context import GameContext

DATA_DIR = "assets/data"


def build_game_context() -> GameContext:
    """Load content, create services and systems, generate the start map."""
    content = default_content.load(DATA_DIR)

    map_service = MapService()
    world_clock = WorldClockService()
    world_graph = WorldGraphService.from_file(f"{DATA_DIR}/world.json")

    # Viewport is the area not covered by UI header and log
    viewport_width = SCREEN_WIDTH - SIDEBAR_WIDTH
    viewport_height = SCREEN_HEIGHT - HEADER_HEIGHT - LOG_HEIGHT
    camera = Camera(viewport_width, viewport_height, 0, HEADER_HEIGHT)

    MapGenerator(map_service).create_world(esper, world_graph)

    systems = build_systems(world_clock, map_service.get_active_map())
    register_processors(systems)

    ctx = GameContext(
        map_service=map_service,
        render_service=RenderService(),
        world_clock=world_clock,
        input_manager=InputManager(),
        ui_stack=UIStack(),
        camera=camera,
        systems=systems,
        world_graph=world_graph,
        content=content,
    )

    # World chronicle: generates off-screen events as game hours pass
    chronicle = WorldChronicleService(ctx=ctx)
    chronicle.load_templates(f"{DATA_DIR}/world_events.json")
    ctx.world_chronicle = chronicle
    esper.set_handler("clock_tick", chronicle.on_clock_tick)

    # Settlement economy: stock levels drift hourly and drive local prices
    economy = EconomyService()
    economy.load_from_world(world_graph, f"{DATA_DIR}/scenarios")
    ctx.economy = economy
    esper.set_handler("clock_tick", economy.on_clock_tick)

    # Player reputation per settlement (registers its entity_died handler)
    ctx.reputation = ReputationService(ctx=ctx)

    # Quests: authored from JSON, generated ones appear on arrival
    quests = QuestService(ctx=ctx)
    quests.load_authored(f"{DATA_DIR}/quests.json")
    ctx.quests = quests

    # Rumors: smalltalk occasionally points at other settlements
    ctx.rumors = RumorService(ctx=ctx)
    default_content.dialogues.rumor_provider = ctx.rumors.maybe_rumor

    # Dialogue selection context: rep tier at the current location + day phase
    def _dialogue_context() -> dict:
        location_id = ctx.world_graph.current_location_id if ctx.world_graph else None
        return {
            "rep": ctx.reputation.tier(location_id) if ctx.reputation else "neutral",
            "phase": ctx.world_clock.phase if ctx.world_clock else "day",
        }

    default_content.dialogues.context_provider = _dialogue_context

    return ctx

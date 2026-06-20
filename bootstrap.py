"""Composition root: builds the complete GameContext exactly once.

All content loading, service construction and system wiring happens here.
Nothing else in the codebase should construct services or systems.
"""

import random

import esper

from config import HEADER_HEIGHT, LOG_HEIGHT, SCREEN_HEIGHT, SCREEN_WIDTH, SIDEBAR_WIDTH
from core.camera import Camera
from core.ecs import apply_esper_compat_patches
from core.input_manager import InputManager
from core.rng import derive_seed
from core.ui.stack_manager import UIStack
from core.world_clock_service import WorldClockService
from game.content.content_database import default_content
from game.services.economy_service import EconomyService
from game.services.faction_service import FactionService
from game.services.map_generator import MapGenerator
from game.services.map_service import MapService
from game.services.merchant_restock_service import MerchantRestockService
from game.services.quest_service import QuestService
from game.services.render_service import RenderService
from game.services.reputation_service import ReputationService
from game.services.rumor_service import RumorService
from game.services.system_initializer import build_systems, register_processors
from game.services.travel_encounter_service import TravelEncounterService
from game.services.world_chronicle_service import WorldChronicleService
from game.services.world_graph_service import WorldGraphService
from game_context import GameContext

DATA_DIR = "assets/data"


def build_game_context(seed: int | None = None) -> GameContext:
    """Load content, create services and systems, generate the start map.

    Args:
        seed: World seed for this run (Phase G1). Every seeded source of
            run variation — wilderness/dungeon layout, chronicle rolls,
            economy jitter — derives from it, so the same seed reproduces
            the same world. None picks a random seed.
    """
    # Work around an esper 3.7 query bug before any entities are created.
    apply_esper_compat_patches()

    world_seed = seed if seed is not None else random.SystemRandom().randrange(2**31)

    content = default_content.load(DATA_DIR)

    map_service = MapService()
    world_clock = WorldClockService()
    world_graph = WorldGraphService.from_file(f"{DATA_DIR}/world.json")

    # Viewport is the area not covered by UI header and log
    viewport_width = SCREEN_WIDTH - SIDEBAR_WIDTH
    viewport_height = SCREEN_HEIGHT - HEADER_HEIGHT - LOG_HEIGHT
    camera = Camera(viewport_width, viewport_height, 0, HEADER_HEIGHT)

    MapGenerator(map_service, seed=derive_seed(world_seed, "maps")).create_world(esper, world_graph)

    systems = build_systems(world_clock, map_service.get_active_map())
    register_processors(systems)
    # Reproducible ambient gossip per world seed (Phase L slice 2)
    systems.gossip_system.rng.seed(derive_seed(world_seed, "gossip"))

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
        world_seed=world_seed,
    )

    # World chronicle: generates off-screen events as game hours pass
    chronicle = WorldChronicleService(ctx=ctx)
    chronicle.rng.seed(derive_seed(world_seed, "chronicle"))
    chronicle.load_templates(f"{DATA_DIR}/world_events.json")
    ctx.world_chronicle = chronicle
    esper.set_handler("clock_tick", chronicle.on_clock_tick)

    # Settlement economy: stock levels drift hourly and drive local prices
    economy = EconomyService()
    economy.load_from_world(world_graph, f"{DATA_DIR}/scenarios")
    economy.apply_variation(random.Random(derive_seed(world_seed, "economy")))
    ctx.economy = economy
    esper.set_handler("clock_tick", economy.on_clock_tick)

    # Shops refill their stock toward the starting menu over time (Phase K)
    restock = MerchantRestockService(economy=economy, world_graph=world_graph)
    ctx.merchant_restock = restock
    esper.set_handler("clock_tick", restock.on_clock_tick)

    # Player reputation per settlement (registers its entity_died handler)
    ctx.reputation = ReputationService(ctx=ctx)

    # Factions: group disposition + per-faction player standing (registers its
    # entity_died handler). Sync alignments once so the starting map reflects
    # any faction that already counts the player an enemy.
    factions = FactionService(ctx=ctx)
    factions.load(f"{DATA_DIR}/factions.json")
    factions.sync_alignments()
    ctx.factions = factions

    # Quests: authored from JSON, generated ones appear on arrival
    quests = QuestService(ctx=ctx)
    quests.rng.seed(derive_seed(world_seed, "quests"))
    quests.load_authored(f"{DATA_DIR}/quests.json")
    ctx.quests = quests

    # Travel encounters: road events between settlements, fed by the chronicle
    travel_encounters = TravelEncounterService(ctx=ctx)
    travel_encounters.rng.seed(derive_seed(world_seed, "travel"))
    travel_encounters.load_templates(f"{DATA_DIR}/travel_encounters.json")
    ctx.travel_encounters = travel_encounters

    # Rumors: smalltalk occasionally points at other settlements; locals give
    # directions out of town the first time you ask (how places become known).
    ctx.rumors = RumorService(ctx=ctx)
    default_content.dialogues.rumor_provider = ctx.rumors.maybe_rumor
    default_content.dialogues.directions_provider = ctx.rumors.directions

    # Dialogue selection context: rep tier at the current location, day
    # phase and the settlement's prosperity tier (G3)
    def _dialogue_context() -> dict:
        location_id = ctx.world_graph.current_location_id if ctx.world_graph else None
        context = {
            "rep": ctx.reputation.tier(location_id) if ctx.reputation else "neutral",
            "phase": ctx.world_clock.phase if ctx.world_clock else "day",
            "prosperity": ctx.economy.prosperity_tier(location_id) if ctx.economy else "stable",
        }
        # Quest-aware smalltalk: givers comment on work in progress here so a
        # conversation reflects what the player owes the settlement (Phase: chains).
        if ctx.quests is not None:
            if ctx.quests.turn_in_candidates(location_id):
                context["quest"] = "ready"
            elif any(q.giver_location == location_id for q in ctx.quests.active_quests()):
                context["quest"] = "active"
        # Faction-aware smalltalk: the guard reacts to the player's standing
        # with the town guard (wary/hostile if you've spilled the wrong blood).
        if ctx.factions is not None:
            context["guards"] = ctx.factions.tier("town_guard")
        return context

    default_content.dialogues.context_provider = _dialogue_context

    return ctx

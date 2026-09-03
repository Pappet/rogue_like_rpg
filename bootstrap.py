"""Composition root: builds the complete GameContext exactly once.

All content loading, service construction and system wiring happens here.
Nothing else in the codebase should construct services or systems.
"""

import random

import esper

from config import HEADER_HEIGHT, LOG_HEIGHT, SCREEN_HEIGHT, SCREEN_WIDTH, SIDEBAR_WIDTH, GameEvent
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

    start_map = map_service.get_active_map()
    if start_map is None:
        raise RuntimeError("World generation produced no active map.")

    systems = build_systems(world_clock, start_map)
    register_processors(systems)
    # Reproducible ambient gossip per world seed (Phase L slice 2)
    systems.gossip_system.rng.seed(derive_seed(world_seed, "gossip"))

    # Services that need the context are constructed first and handed it
    # afterwards: the context cannot exist before its own fields do, and
    # every one of them is a required field (no None to paper over the gap).
    chronicle = WorldChronicleService()
    chronicle.rng.seed(derive_seed(world_seed, "chronicle"))
    chronicle.load_templates(f"{DATA_DIR}/world_events.json")

    economy = EconomyService()
    economy.load_from_world(world_graph, f"{DATA_DIR}/scenarios")
    economy.apply_variation(random.Random(derive_seed(world_seed, "economy")))

    # Shops refill their stock toward the starting menu over time (Phase K)
    restock = MerchantRestockService(economy=economy, world_graph=world_graph)

    # Reputation and factions register their own entity_died handlers
    reputation = ReputationService()
    factions = FactionService()
    factions.load(f"{DATA_DIR}/factions.json")

    # Quests: authored from JSON, generated ones appear on arrival
    quests = QuestService()
    quests.rng.seed(derive_seed(world_seed, "quests"))
    quests.load_authored(f"{DATA_DIR}/quests.json")

    # Travel encounters: road events between settlements, fed by the chronicle
    travel_encounters = TravelEncounterService()
    travel_encounters.rng.seed(derive_seed(world_seed, "travel"))
    travel_encounters.load_templates(f"{DATA_DIR}/travel_encounters.json")

    # Rumors: smalltalk occasionally points at other settlements; locals give
    # directions out of town the first time you ask (how places become known).
    rumors = RumorService()

    ctx = GameContext(
        map_service=map_service,
        render_service=RenderService(),
        world_clock=world_clock,
        input_manager=InputManager(),
        ui_stack=UIStack(),
        camera=camera,
        systems=systems,
        content=content,
        world_graph=world_graph,
        world_chronicle=chronicle,
        economy=economy,
        merchant_restock=restock,
        reputation=reputation,
        factions=factions,
        quests=quests,
        rumors=rumors,
        travel_encounters=travel_encounters,
        world_seed=world_seed,
    )

    for service in (chronicle, reputation, factions, quests, travel_encounters, rumors):
        service.ctx = ctx

    # Hourly world simulation: chronicle events, economy drift, shop restock
    esper.set_handler(GameEvent.CLOCK_TICK, chronicle.on_clock_tick)
    esper.set_handler(GameEvent.CLOCK_TICK, economy.on_clock_tick)
    esper.set_handler(GameEvent.CLOCK_TICK, restock.on_clock_tick)

    # The starting map must reflect any faction that already counts the player
    # an enemy — needs the context, so it runs after the wiring above.
    factions.sync_alignments()

    default_content.dialogues.rumor_provider = ctx.rumors.maybe_rumor
    default_content.dialogues.directions_provider = ctx.rumors.directions

    # Dialogue selection context: rep tier at the current location, day
    # phase and the settlement's prosperity tier (G3)
    def _dialogue_context() -> dict:
        location_id = ctx.world_graph.current_location_id
        context = {
            "rep": ctx.reputation.tier(location_id),
            "phase": ctx.world_clock.phase,
            "prosperity": ctx.economy.prosperity_tier(location_id),
            # The town's purse: the mayor is the one who knows what is in it,
            # and it is where the market toll goes and rewards come from.
            "treasury": ctx.economy.treasury_tier(location_id),
            # The guard reacts to the player's standing with the town guard
            # (wary or hostile if you have spilled the wrong blood).
            "guards": ctx.factions.tier("town_guard"),
        }
        # Quest-aware smalltalk: givers comment on work in progress here so a
        # conversation reflects what the player owes the settlement (chains).
        if ctx.quests.turn_in_candidates(location_id):
            context["quest"] = "ready"
        elif any(q.giver_location == location_id for q in ctx.quests.active_quests()):
            context["quest"] = "active"
        return context

    default_content.dialogues.context_provider = _dialogue_context

    return ctx

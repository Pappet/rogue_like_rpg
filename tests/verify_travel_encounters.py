"""Travel encounters: road events between settlements.

Covers:
- encounter chance scales with route length (capped),
- the one-shot road map (walkable road, portals carrying the split
  travel time, staged NPC scene),
- the chronicle tie-in (a merchant who left the destination is met on
  the road toward it),
- skirmish AI (two factions fight each other, not the player),
- the end-to-end journey: world map -> road event -> continue portal ->
  destination, with the clock advancing exactly the route's ticks.

Run from project root:
    python -m pytest tests/verify_travel_encounters.py -v
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from types import SimpleNamespace

import esper
import pygame

from config import (
    TICKS_PER_HOUR,
    TRAVEL_ENCOUNTER_MAX_CHANCE,
    TRAVEL_ENCOUNTER_MAX_PROGRESS,
    TRAVEL_ENCOUNTER_MIN_PROGRESS,
    GameStates,
)
from core.world_clock_service import WorldClockService
from game.components import (
    AI,
    AIBehaviorState,
    AIState,
    Alignment,
    AttackIntent,
    ChaseData,
    Merchant,
    PlayerTag,
    Portal,
    Position,
    Skirmisher,
    Stats,
)
from game.content.content_database import default_content
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.map_service import MapService
from game.services.travel_encounter_service import (
    MERCHANT_ENCOUNTER_ID,
    TravelEncounterService,
    is_road_map,
    road_map_id,
)
from game.services.world_chronicle_service import WorldChronicleService
from game.systems.ai_system import AISystem
from game.systems.turn_system import TurnSystem

DATA_DIR = "assets/data"
ROUTE_TICKS = 720  # Village <-> Eastmoor


def _flat_container(width=12, height=12) -> MapContainer:
    tiles = [[Tile(type_id="floor_stone") for _ in range(width)] for _ in range(height)]
    return MapContainer([MapLayer(tiles)], arrival_pos=(1, 1))


def _make_service():
    """Service against a minimal ctx: two settlement maps 'A' and 'B'."""
    default_content.load(DATA_DIR)
    map_service = MapService()
    map_service.register_map("A", _flat_container())
    map_service.register_map("B", _flat_container())
    map_service.set_active_map("A")
    ctx = SimpleNamespace(map_service=map_service, world_chronicle=None, world_clock=None)
    service = TravelEncounterService(ctx=ctx)
    service.load_templates(f"{DATA_DIR}/travel_encounters.json")
    return service, ctx


# --- Probability ----------------------------------------------------------------


def test_chance_scales_with_travel_time_and_is_capped():
    service, _ = _make_service()
    short = service.encounter_chance(6 * TICKS_PER_HOUR)
    long = service.encounter_chance(12 * TICKS_PER_HOUR)
    assert short < long
    assert service.encounter_chance(1000 * TICKS_PER_HOUR) == TRAVEL_ENCOUNTER_MAX_CHANCE


def test_no_encounter_on_high_roll():
    service, ctx = _make_service()
    service.rng.random = lambda: 0.99
    assert service.roll_encounter("A", "B", ROUTE_TICKS) is None
    assert road_map_id("A", "B") not in ctx.map_service.maps


# --- Road map & scene -----------------------------------------------------------


def test_roll_builds_road_map_partway_into_the_journey():
    service, ctx = _make_service()
    service.rng.random = lambda: 0.0  # force the encounter
    result = service.roll_encounter("A", "B", ROUTE_TICKS)

    assert result is not None
    assert is_road_map(result["map_id"])
    container = ctx.map_service.get_map(result["map_id"])
    assert container is not None
    ax, ay = container.arrival_pos
    assert container.is_walkable(ax, ay)
    # The journey is interrupted partway — never at the very start or end
    assert result["elapsed_ticks"] >= TRAVEL_ENCOUNTER_MIN_PROGRESS * ROUTE_TICKS
    assert result["elapsed_ticks"] <= TRAVEL_ENCOUNTER_MAX_PROGRESS * ROUTE_TICKS


def test_entering_road_map_spawns_portals_and_scene():
    service, ctx = _make_service()
    service.rng.random = lambda: 0.0  # forces the first template: traveling merchant
    result = service.roll_encounter("A", "B", ROUTE_TICKS)
    service.on_map_entered(result["map_id"])

    portals = {portal.target_map_id: portal for _, (portal,) in esper.get_components(Portal)}
    assert set(portals) == {"A", "B"}
    # Continue-portal carries the remaining travel time, turn-back the elapsed
    assert portals["B"].travel_ticks == ROUTE_TICKS - result["elapsed_ticks"]
    assert portals["A"].travel_ticks == result["elapsed_ticks"]

    merchants = list(esper.get_components(Merchant, Position))
    assert merchants, "the traveling merchant must stand on the road"

    # The scene is staged exactly once
    service.on_map_entered(result["map_id"])
    assert len(list(esper.get_components(Portal))) == 2


def test_road_map_is_dropped_after_leaving():
    service, ctx = _make_service()
    service.rng.random = lambda: 0.0
    result = service.roll_encounter("A", "B", ROUTE_TICKS)
    map_id = result["map_id"]

    # Still active (player on the road): must NOT be dropped
    ctx.map_service.set_active_map(map_id)
    service.on_map_left(map_id)
    assert map_id in ctx.map_service.maps

    # Player has moved on: one-shot map goes away
    ctx.map_service.set_active_map("B")
    service.on_map_left(map_id)
    assert map_id not in ctx.map_service.maps
    # Settlement maps are never dropped
    service.on_map_left("A")
    assert "A" in ctx.map_service.maps


# --- Chronicle tie-in -----------------------------------------------------------


def test_merchant_who_left_destination_is_met_on_the_road():
    service, ctx = _make_service()
    ctx.world_clock = WorldClockService()
    ctx.world_chronicle = WorldChronicleService()
    ctx.world_chronicle.record("B", tick=1, text="A traveling merchant left B.", event_id="merchant_left")

    # 0.4 fails the base roll for this route (chance 0.3) but passes the
    # merchant rumor roll (0.5) — only the chronicle event makes it happen.
    service.rng.random = lambda: 0.4
    result = service.roll_encounter("A", "B", 6 * TICKS_PER_HOUR)
    assert result is not None
    assert service._pending["template"].id == MERCHANT_ENCOUNTER_ID
    assert "B" in result["message"]


def test_without_chronicle_event_same_roll_yields_nothing():
    service, ctx = _make_service()
    ctx.world_clock = WorldClockService()
    ctx.world_chronicle = WorldChronicleService()  # no merchant_left recorded
    service.rng.random = lambda: 0.4
    assert service.roll_encounter("A", "B", 6 * TICKS_PER_HOUR) is None


# --- Skirmish AI (TRVE-01/02) ---------------------------------------------------


def _skirmisher(x, y, side, alignment=Alignment.HOSTILE):
    return esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=alignment),
        Position(x, y, 0),
        Stats(hp=10, max_hp=10, power=2, defense=0, mana=0, max_mana=0, perception=8, intelligence=3),
        Skirmisher(side=side),
    )


def _enemy_turn():
    turn = TurnSystem()
    turn.end_player_turn()
    assert turn.current_state == GameStates.ENEMY_TURN
    return turn


def test_skirmishers_close_in_and_attack_each_other():
    default_content.load(DATA_DIR)
    container = _flat_container()
    a = _skirmisher(2, 2, "guards", alignment=Alignment.NEUTRAL)
    b = _skirmisher(6, 2, "raiders")

    AISystem().process(_enemy_turn(), container, player_layer=0)
    pos_a, pos_b = esper.component_for_entity(a, Position), esper.component_for_entity(b, Position)
    assert pos_b.x - pos_a.x < 4, "skirmishers must step toward each other"

    # Adjacent fighters trade blows instead of moving
    pos_a.x, pos_a.y, pos_b.x, pos_b.y = 2, 2, 3, 2
    AISystem().process(_enemy_turn(), container, player_layer=0)
    assert esper.component_for_entity(a, AttackIntent).target_entity == b
    assert esper.component_for_entity(b, AttackIntent).target_entity == a


def test_skirmisher_ignores_player_while_fighting():
    default_content.load(DATA_DIR)
    container = _flat_container()
    player = esper.create_entity(PlayerTag(), Position(3, 3, 0))
    goblin = _skirmisher(2, 2, "raiders")
    _skirmisher(6, 2, "guards", alignment=Alignment.NEUTRAL)

    AISystem().process(_enemy_turn(), container, player_layer=0, player_entity=player)
    assert not esper.has_component(goblin, ChaseData), "a fighter locked in battle must not chase the player"
    intent = esper.try_component(goblin, AttackIntent)
    assert intent is None or intent.target_entity != player


def test_skirmish_ends_when_no_opponents_remain():
    default_content.load(DATA_DIR)
    container = _flat_container()
    lone = _skirmisher(2, 2, "guards", alignment=Alignment.NEUTRAL)

    AISystem().process(_enemy_turn(), container, player_layer=0)
    assert not esper.has_component(lone, Skirmisher), "without opponents the skirmish is over"


# --- End-to-end: world map -> road event -> destination ---------------------------


def _boot():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    gc.state_name = "GAME"
    gc.state = game
    game.startup(gc.ctx)
    return gc, game


def _frames(gc, n=5, dt=0.016):
    surface = pygame.display.get_surface()
    for _ in range(n):
        gc.state.update(dt)
        gc.state.draw(surface)


def _key(gc, key):
    gc.state.get_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
    if gc.state.done:
        gc.flip_state()


def test_travel_encounter_end_to_end():
    gc, game = _boot()
    _frames(gc)
    ctx = gc.ctx
    ctx.world_graph.reveal_routes_from(ctx.world_graph.current_location_id)  # ask for directions
    ctx.travel_encounters.rng.random = lambda: 0.0  # force an encounter on this trip
    ticks_before = ctx.world_clock.total_ticks

    _key(gc, pygame.K_m)
    world_map = gc.state
    destination, route_ticks = world_map.destinations[world_map.selected_idx]
    _key(gc, pygame.K_RETURN)

    # The journey was interrupted partway on a road map
    assert gc.state_name == "GAME"
    road_id = ctx.map_service.active_map_id
    assert is_road_map(road_id)
    elapsed = ctx.world_clock.total_ticks - ticks_before
    assert 0 < elapsed < route_ticks
    assert ctx.world_graph.current_location_id != destination.id

    # The game keeps running on the road (the scene acts)
    _frames(gc)
    assert game.turn_system.current_state == GameStates.PLAYER_TURN

    # Step onto the continue-portal and use it
    portal_entry = next(
        (pos, portal)
        for _, (pos, portal) in esper.get_components(Position, Portal)
        if portal.target_map_id == destination.id
    )
    p_pos, portal = portal_entry
    assert portal.travel_ticks == route_ticks - elapsed
    player_pos = esper.component_for_entity(ctx.player_entity, Position)
    player_pos.x, player_pos.y = p_pos.x, p_pos.y
    _frames(gc, 2)
    _key(gc, pygame.K_g)
    _frames(gc)

    # Arrived: full route time has passed (+1 tick for the portal turn
    # itself), and the one-shot road map is gone
    assert ctx.map_service.active_map_id == destination.id
    assert ctx.world_graph.current_location_id == destination.id
    assert ctx.world_clock.total_ticks - ticks_before == route_ticks + 1
    assert road_id not in ctx.map_service.maps

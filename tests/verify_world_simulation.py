"""Tests for off-screen schedule reconciliation (ROADMAP Phase B)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from config import SIM_RECONCILE_MIN_TICKS
from game.components import Activity, AIBehaviorState, AIState, Alignment, PathData, Position, Schedule
from game.content.resource_loader import ResourceLoader
from game.content.schedule_registry import ScheduleEntry, ScheduleTemplate, schedule_registry
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.world_simulation_service import WorldSimulationService

# ---------------------------------------------------------------------------
# Unit tests on a synthetic map/schedule
# ---------------------------------------------------------------------------


def _open_map(size=20) -> MapContainer:
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    tiles = [[Tile(type_id="floor_stone") for _ in range(size)] for _ in range(size)]
    return MapContainer([MapLayer(tiles)])


def _register_smith_schedule():
    schedule_registry.register(
        ScheduleTemplate(
            id="smith_test",
            name="Smith",
            entries=[
                ScheduleEntry(start=0, end=6, activity="SLEEP", target_meta="home"),
                ScheduleEntry(start=6, end=18, activity="WORK", target_pos=(15, 15)),
                ScheduleEntry(start=18, end=24, activity="SLEEP", target_meta="home"),
            ],
        )
    )


def _spawn_smith(x=2, y=2, home=(3, 3)):
    return esper.create_entity(
        Position(x, y, 0),
        Schedule(schedule_id="smith_test"),
        Activity(current_activity="IDLE", home_pos=home),
        AIBehaviorState(AIState.IDLE, Alignment.NEUTRAL),
    )


def test_npc_snaps_to_work_position():
    container = _open_map()
    _register_smith_schedule()
    smith = _spawn_smith(x=2, y=2)

    moved = WorldSimulationService.reconcile_arrivals(esper, container, hour=14, elapsed_ticks=720)
    assert moved == 1

    pos = esper.component_for_entity(smith, Position)
    assert (pos.x, pos.y) == (15, 15)
    behavior = esper.component_for_entity(smith, AIBehaviorState)
    assert behavior.state is AIState.WORK
    activity = esper.component_for_entity(smith, Activity)
    assert activity.current_activity == "WORK"


def test_npc_snaps_home_and_sleeps_at_night():
    container = _open_map()
    _register_smith_schedule()
    smith = _spawn_smith(x=15, y=15, home=(3, 3))

    WorldSimulationService.reconcile_arrivals(esper, container, hour=23, elapsed_ticks=720)

    pos = esper.component_for_entity(smith, Position)
    assert (pos.x, pos.y) == (3, 3)
    assert esper.component_for_entity(smith, AIBehaviorState).state is AIState.SLEEP


def test_short_absence_does_not_teleport():
    container = _open_map()
    _register_smith_schedule()
    smith = _spawn_smith(x=2, y=2)

    moved = WorldSimulationService.reconcile_arrivals(
        esper, container, hour=14, elapsed_ticks=SIM_RECONCILE_MIN_TICKS - 1
    )
    assert moved == 0
    pos = esper.component_for_entity(smith, Position)
    assert (pos.x, pos.y) == (2, 2)


def test_stale_paths_are_cleared():
    container = _open_map()
    _register_smith_schedule()
    smith = _spawn_smith(x=2, y=2)
    esper.add_component(smith, PathData(path=[(2, 3), (2, 4)], destination=(2, 4)))

    WorldSimulationService.reconcile_arrivals(esper, container, hour=14, elapsed_ticks=720)
    assert not esper.has_component(smith, PathData)


def test_two_npcs_same_target_do_not_stack():
    """SIM-NOCOL: Reconciliation must not place two NPCs on the same tile."""
    container = _open_map()
    _register_smith_schedule()
    smith1 = _spawn_smith(x=2, y=2)
    smith2 = _spawn_smith(x=3, y=3)

    WorldSimulationService.reconcile_arrivals(esper, container, hour=14, elapsed_ticks=720)

    pos1 = esper.component_for_entity(smith1, Position)
    pos2 = esper.component_for_entity(smith2, Position)
    assert (pos1.x, pos1.y) != (pos2.x, pos2.y), (
        "Two NPCs with the same schedule target must not be placed on the same tile"
    )


def test_npc_not_placed_on_door_tile():
    """SIM-NODOOR: Reconciliation must not place an NPC directly on a door tile."""
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    size = 20
    tiles = [[Tile(type_id="floor_stone") for _ in range(size)] for _ in range(size)]
    # Make the exact work target (15, 15) a door tile
    tiles[15][15] = Tile(type_id="door_stone")
    container = MapContainer([MapLayer(tiles)])
    _register_smith_schedule()
    smith = _spawn_smith(x=2, y=2)

    WorldSimulationService.reconcile_arrivals(esper, container, hour=14, elapsed_ticks=720)

    pos = esper.component_for_entity(smith, Position)
    placed_tile = container.layers[0].tiles[pos.y][pos.x]
    assert placed_tile.type_id not in {"door_stone", "door_wood"}, (
        "NPC must not be placed directly on a door tile when floor tiles are available nearby"
    )


def test_home_meta_without_home_pos_keeps_position():
    container = _open_map()
    _register_smith_schedule()
    smith = _spawn_smith(x=7, y=7, home=None)

    moved = WorldSimulationService.reconcile_arrivals(esper, container, hour=23, elapsed_ticks=720)
    assert moved == 0
    pos = esper.component_for_entity(smith, Position)
    assert (pos.x, pos.y) == (7, 7)
    # State still follows the schedule
    assert esper.component_for_entity(smith, AIBehaviorState).state is AIState.SLEEP


# ---------------------------------------------------------------------------
# End-to-end: travel away and back, NPCs follow their day plan
# ---------------------------------------------------------------------------


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


def _key(gc, key):
    gc.state.get_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
    if gc.state.done:
        gc.flip_state()


def _frames(gc, n=5, dt=0.016):
    surface = pygame.display.get_surface()
    for _ in range(n):
        gc.state.update(dt)
        gc.state.draw(surface)


def test_travel_roundtrip_reconciles_village_npcs():
    gc, _game = _boot()
    ctx = gc.ctx
    ctx.world_graph.reveal_routes_from(ctx.world_graph.current_location_id)  # ask for directions
    ctx.travel_encounters.templates = []  # deterministic direct travel, no road events
    _frames(gc)

    # Travel to the first destination and straight back: half a day or more
    # passes, so Village NPCs must be re-placed by schedule, not frozen pose.
    _key(gc, pygame.K_m)
    destination, _ticks = gc.state.destinations[gc.state.selected_idx]
    _key(gc, pygame.K_RETURN)
    assert ctx.map_service.active_map_id == destination.id
    _frames(gc)

    _key(gc, pygame.K_m)
    back = [i for i, (loc, _) in enumerate(gc.state.destinations) if loc.id == "Village"]
    assert back, "Village must be reachable from the destination"
    for _ in range(back[0]):
        _key(gc, pygame.K_DOWN)
    _key(gc, pygame.K_RETURN)
    assert ctx.map_service.active_map_id == "Village"
    _frames(gc)

    # Every scheduled NPC's activity matches its schedule for the current hour
    hour = ctx.world_clock.hour
    checked = 0
    for _ent, (sched, activity) in esper.get_components(Schedule, Activity):
        template = schedule_registry.get(sched.schedule_id)
        if template is None:
            continue
        entry = template.entry_for_hour(hour)
        if entry is None:
            continue
        assert activity.current_activity == entry.activity.upper(), (
            f"NPC activity '{activity.current_activity}' does not match "
            f"schedule entry '{entry.activity}' for hour {hour}"
        )
        checked += 1
    assert checked >= 1, "expected at least one scheduled NPC in the Village"

    # The game keeps running
    _key(gc, pygame.K_SPACE)
    _frames(gc)

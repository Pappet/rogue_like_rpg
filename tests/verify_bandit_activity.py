"""Bandit activity on the roads (Phase G4).

A ``bandits_spotted`` chronicle event at the destination makes the road
there dangerous: the travel encounter is biased toward a bandit ambush.
Clearing the ambush resolves the threat — the pending ``caravan_raided``
escalation at the destination is cancelled.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from types import SimpleNamespace

import esper

from config import TICKS_PER_HOUR
from core.world_clock_service import WorldClockService
from game.content.content_database import default_content
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.map_service import MapService
from game.services.travel_encounter_service import (
    BANDIT_ENCOUNTER_ID,
    BANDITS_SPOTTED_EVENT_ID,
    TravelEncounterService,
)
from game.services.world_chronicle_service import WorldChronicleService
from game.services.world_graph_service import WorldGraphService, WorldLocation

DATA_DIR = "assets/data"


def _flat_container(width=12, height=12) -> MapContainer:
    tiles = [[Tile(type_id="floor_stone") for _ in range(width)] for _ in range(height)]
    return MapContainer([MapLayer(tiles)], arrival_pos=(1, 1))


def _make_service():
    default_content.load(DATA_DIR)
    map_service = MapService()
    map_service.register_map("A", _flat_container())
    map_service.register_map("B", _flat_container())
    map_service.set_active_map("A")

    graph = WorldGraphService()
    graph.add_location(WorldLocation(id="A", name="A", discovered=True))
    graph.add_location(WorldLocation(id="B", name="B", discovered=True))
    graph.current_location_id = "A"

    ctx = SimpleNamespace(
        map_service=map_service,
        world_clock=WorldClockService(),
        world_chronicle=None,
        world_graph=graph,
        economy=None,
    )
    chronicle = WorldChronicleService(ctx=ctx)
    chronicle.load_templates(f"{DATA_DIR}/world_events.json")
    ctx.world_chronicle = chronicle

    service = TravelEncounterService(ctx=ctx)
    service.load_templates(f"{DATA_DIR}/travel_encounters.json")
    return service, ctx


def _spot_bandits(ctx, location_id="B"):
    """Fire the real bandits_spotted template (schedules the raid)."""
    chronicle = ctx.world_chronicle
    template = chronicle.template_by_id(BANDITS_SPOTTED_EVENT_ID)
    chronicle._fire(template, ctx.world_graph.get_location(location_id), hour_index=0)


# ---------------------------------------------------------------------------
# Chronicle tie-in: spotted bandits hold the road
# ---------------------------------------------------------------------------


def test_spotted_bandits_bias_the_road_encounter():
    service, ctx = _make_service()
    _spot_bandits(ctx)

    # 0.4 fails the base encounter roll for this route but passes the
    # bandit roll (0.6) — only the chronicle event makes it happen.
    service.rng.random = lambda: 0.4
    result = service.roll_encounter("A", "B", 6 * TICKS_PER_HOUR)
    assert result is not None
    assert service._pending["template"].id == BANDIT_ENCOUNTER_ID


def test_without_bandit_event_same_roll_yields_nothing():
    service, _ = _make_service()
    service.rng.random = lambda: 0.4
    assert service.roll_encounter("A", "B", 6 * TICKS_PER_HOUR) is None


def test_old_sightings_expire():
    service, ctx = _make_service()
    _spot_bandits(ctx)
    ctx.world_clock.total_ticks = 10 * 24 * TICKS_PER_HOUR  # ten days later
    service.rng.random = lambda: 0.4
    assert service.roll_encounter("A", "B", 6 * TICKS_PER_HOUR) is None


# ---------------------------------------------------------------------------
# Clearing the ambush cancels the caravan raid
# ---------------------------------------------------------------------------


def _enter_ambush(service, ctx):
    service.rng.random = lambda: 0.4
    result = service.roll_encounter("A", "B", 6 * TICKS_PER_HOUR)
    ctx.map_service.set_active_map(result["map_id"])
    service.on_map_entered(result["map_id"])
    return result


def test_clearing_the_ambush_cancels_the_escalation():
    service, ctx = _make_service()
    _spot_bandits(ctx)
    assert len(ctx.world_chronicle.pending_escalations) == 1

    _enter_ambush(service, ctx)
    from game.components import AI, TemplateId

    bandits = [ent for ent, (tid, _ai) in esper.get_components(TemplateId, AI) if tid.id in ("bandit", "bandit_leader")]
    assert len(bandits) == 3, "the staged ambush should field three bandits"

    # Strike them down one by one — only the last kill resolves the threat
    for bandit in bandits[:-1]:
        esper.remove_component(bandit, AI)
        service.on_entity_died(bandit)
        assert ctx.world_chronicle.pending_escalations, "the raid is still coming while bandits stand"
    esper.remove_component(bandits[-1], AI)
    service.on_entity_died(bandits[-1])

    assert not ctx.world_chronicle.pending_escalations, "a cleared road means no caravan raid"


def test_riding_past_the_ambush_keeps_the_threat():
    service, ctx = _make_service()
    _spot_bandits(ctx)
    result = _enter_ambush(service, ctx)

    ctx.map_service.set_active_map("B")
    service.on_map_left(result["map_id"])

    assert ctx.world_chronicle.pending_escalations, "unfought bandits still raid the caravans"
    assert service._bandit_hunt is None


# ---------------------------------------------------------------------------
# Content sanity
# ---------------------------------------------------------------------------


def test_bandit_templates_exist_and_are_hostile():
    from game.components import AIBehaviorState, Alignment
    from game.content.entity_factory import EntityFactory

    default_content.load(DATA_DIR)
    for template_id in ("bandit", "bandit_leader"):
        ent = EntityFactory.create(esper, template_id, 1, 1)
        behavior = esper.component_for_entity(ent, AIBehaviorState)
        assert behavior.alignment == Alignment.HOSTILE

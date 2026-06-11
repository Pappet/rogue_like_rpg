"""Tests for the NeedsSystem (ROADMAP Phase D1: needs preempt schedules)."""

import esper

from config import TICKS_PER_HOUR
from game.components import (
    Activity,
    AIBehaviorState,
    AIState,
    Alignment,
    Needs,
    PathData,
    Position,
    Schedule,
)
from game.content.resource_loader import ResourceLoader
from game.content.schedule_registry import ScheduleEntry, ScheduleTemplate, schedule_registry
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.systems.needs_system import NeedsSystem
from game.systems.schedule_system import ScheduleSystem


def _open_map(size=20) -> MapContainer:
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    tiles = [[Tile(type_id="floor_stone") for _ in range(size)] for _ in range(size)]
    return MapContainer([MapLayer(tiles)])


def _hungry_npc(x=5, y=5, home=(2, 2), hunger=75.0):
    return esper.create_entity(
        Position(x, y, 0),
        Activity(current_activity="WORK", target_pos=(10, 10), home_pos=home),
        AIBehaviorState(AIState.WORK, Alignment.NEUTRAL),
        Needs(hunger=hunger, hunger_rate=2.0, eat_threshold=70.0, eat_duration_ticks=3),
    )


def test_hunger_rises_over_time():
    container = _open_map()
    npc = _hungry_npc(hunger=0.0)
    system = NeedsSystem()
    for _ in range(TICKS_PER_HOUR):
        system.process(container)
    needs = esper.component_for_entity(npc, Needs)
    assert abs(needs.hunger - 2.0) < 0.01, "one hour should add hunger_rate points"


def test_hungry_npc_overrides_schedule_and_heads_home():
    container = _open_map()
    npc = _hungry_npc(hunger=75.0, home=(2, 2))
    NeedsSystem().process(container)

    activity = esper.component_for_entity(npc, Activity)
    assert activity.need_override == "EAT"
    assert activity.current_activity == "EAT"
    assert activity.target_pos == (2, 2)
    assert esper.has_component(npc, PathData), "the NPC should have a path home"


def test_eating_resets_hunger_and_resumes_schedule():
    container = _open_map()
    npc = _hungry_npc(hunger=75.0, home=(5, 5))  # already at home
    system = NeedsSystem()
    system.process(container)  # starts the override (at target already)
    for _ in range(5):  # eat_duration_ticks=3
        system.process(container)

    needs = esper.component_for_entity(npc, Needs)
    activity = esper.component_for_entity(npc, Activity)
    # Hunger was reset to 0 when the meal ended (and may have crept up a
    # fraction of a point in the ticks since).
    assert needs.hunger < 1.0
    assert activity.need_override is None
    assert not esper.has_component(npc, PathData)


def test_schedule_system_skips_overridden_npcs():
    container = _open_map()
    schedule_registry.register(
        ScheduleTemplate(
            id="work_all_day",
            name="Work",
            entries=[ScheduleEntry(start=0, end=24, activity="WORK", target_pos=(10, 10))],
        )
    )
    npc = _hungry_npc(hunger=75.0, home=(2, 2))
    esper.add_component(npc, Schedule(schedule_id="work_all_day"))

    NeedsSystem().process(container)  # override active, heading home

    class _Clock:
        hour = 12

    ScheduleSystem().process(_Clock(), container)

    activity = esper.component_for_entity(npc, Activity)
    assert activity.current_activity == "EAT", "schedule must not stomp an active need override"
    assert activity.target_pos == (2, 2)


def test_needs_never_preempt_chase_or_sleep():
    container = _open_map()
    npc = _hungry_npc(hunger=99.0)
    behavior = esper.component_for_entity(npc, AIBehaviorState)
    behavior.state = AIState.CHASE

    NeedsSystem().process(container)
    activity = esper.component_for_entity(npc, Activity)
    assert activity.need_override is None

    behavior.state = AIState.SLEEP
    NeedsSystem().process(container)
    assert activity.need_override is None

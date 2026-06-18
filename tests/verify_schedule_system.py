import os
import sys
from unittest.mock import MagicMock

import esper

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.components import (
    Activity,
    AIBehaviorState,
    AIState,
    Alignment,
    PathData,
    PatrolRoute,
    Position,
    Residence,
    Schedule,
)
from game.content.schedule_registry import ScheduleEntry, ScheduleTemplate, schedule_registry
from game.services.pathfinding_service import PathfindingService
from game.systems.schedule_system import ScheduleSystem


def _mock_map():
    map_container = MagicMock()
    map_container.width = 30
    map_container.height = 30
    map_container.is_walkable.return_value = True
    PathfindingService.get_path = MagicMock(side_effect=lambda w, m, start, end, layer: [end])
    return map_container


def test_patrol_route_cycles_waypoints():
    """A PATROL entry with a route cycles through its waypoints and advances
    when the guard reaches the current one."""
    esper.clear_database()
    schedule_system = ScheduleSystem()
    route = [(2, 2), (8, 2), (8, 8), (2, 8)]
    schedule_registry.register(
        ScheduleTemplate(
            id="patrol_test",
            name="Patrol",
            entries=[ScheduleEntry(start=0, end=24, activity="PATROL", route=route)],
        )
    )
    ent = esper.create_entity(
        Schedule("patrol_test"),
        AIBehaviorState(AIState.IDLE, Alignment.NEUTRAL),
        Activity(),
        Position(x=route[0][0], y=route[0][1], layer=0),
    )
    clock = MagicMock()
    clock.hour = 10
    container = _mock_map()

    schedule_system.process(clock, container)
    pr = esper.component_for_entity(ent, PatrolRoute)
    behavior = esper.component_for_entity(ent, AIBehaviorState)
    activity = esper.component_for_entity(ent, Activity)
    assert behavior.state == AIState.PATROL
    assert activity.current_activity == "PATROL"
    # Starting on waypoint 0 -> advanced to waypoint 1 as the next target.
    assert activity.target_pos == route[pr.index]
    first_target = activity.target_pos

    # Walk onto the current target; next process advances again.
    pos = esper.component_for_entity(ent, Position)
    pos.x, pos.y = first_target
    schedule_system.process(clock, container)
    assert activity.target_pos != first_target, "reaching a waypoint advances the beat"


def test_patrol_route_staggers_guards():
    """Two guards sharing a route start on different legs so they do not march
    as one pack."""
    esper.clear_database()
    schedule_system = ScheduleSystem()
    route = [(2, 2), (8, 2), (8, 8), (2, 8)]
    schedule_registry.register(
        ScheduleTemplate(
            id="patrol_stagger",
            name="Patrol",
            entries=[ScheduleEntry(start=0, end=24, activity="PATROL", route=route)],
        )
    )
    ents = [
        esper.create_entity(
            Schedule("patrol_stagger"),
            AIBehaviorState(AIState.IDLE, Alignment.NEUTRAL),
            Activity(),
            Position(x=20, y=20, layer=0),
        )
        for _ in range(4)
    ]
    clock = MagicMock()
    clock.hour = 8
    container = _mock_map()
    schedule_system.process(clock, container)

    start_indices = {esper.component_for_entity(e, PatrolRoute).index for e in ents}
    assert len(start_indices) > 1, "guards should not all start on the same waypoint"


def test_target_pool_spreads_npcs():
    """NPCs sharing a schedule with a target_pool fan out across its spots."""
    esper.clear_database()
    schedule_system = ScheduleSystem()
    pool = [(3, 3), (6, 6), (9, 9)]
    schedule_registry.register(
        ScheduleTemplate(
            id="pool_test",
            name="Pool",
            entries=[ScheduleEntry(start=0, end=24, activity="WORK", target_pool=pool)],
        )
    )
    ents = [
        esper.create_entity(
            Schedule("pool_test"),
            AIBehaviorState(AIState.IDLE, Alignment.NEUTRAL),
            Activity(),
            Position(x=0, y=0, layer=0),
        )
        for _ in range(6)
    ]
    clock = MagicMock()
    clock.hour = 12
    container = _mock_map()
    schedule_system.process(clock, container)

    targets = {esper.component_for_entity(e, Activity).target_pos for e in ents}
    assert len(targets) > 1, "a shared pool should send NPCs to more than one spot"
    for t in targets:
        assert t in pool


def test_bedless_npc_gathers_at_night():
    """A bedless NPC heads for its gather spot at night and socialises there,
    while the activity key stays SLEEP (schedule invariant)."""
    esper.clear_database()
    schedule_system = ScheduleSystem()
    schedule_registry.register(
        ScheduleTemplate(
            id="homeless_test",
            name="Homeless",
            entries=[ScheduleEntry(start=0, end=24, activity="SLEEP", target_meta="home")],
        )
    )
    ent = esper.create_entity(
        Schedule("homeless_test"),
        AIBehaviorState(AIState.WORK, Alignment.NEUTRAL),
        Activity(home_pos=(1, 1)),
        Position(x=5, y=5, layer=0),
        Residence(hearth_pos=(7, 7), housed=False, gather_pos=(7, 7)),
    )
    clock = MagicMock()
    clock.hour = 2
    container = _mock_map()
    schedule_system.process(clock, container)

    activity = esper.component_for_entity(ent, Activity)
    behavior = esper.component_for_entity(ent, AIBehaviorState)
    assert activity.current_activity == "SLEEP", "schedule invariant: activity matches the entry"
    assert activity.target_pos == (7, 7), "bedless NPC drifts to its gather spot"
    assert behavior.state == AIState.SOCIALIZE, "it mills about the fire instead of sleeping"


def test_hearth_meta_uses_residence():
    """A SOCIALIZE entry with target_meta 'hearth' resolves to the NPC's
    Residence.hearth_pos (the village's real campfire)."""
    esper.clear_database()
    schedule_system = ScheduleSystem()
    schedule_registry.register(
        ScheduleTemplate(
            id="hearth_test",
            name="Hearth",
            entries=[ScheduleEntry(start=0, end=24, activity="SOCIALIZE", target_meta="hearth", target_pos=(1, 1))],
        )
    )
    ent = esper.create_entity(
        Schedule("hearth_test"),
        AIBehaviorState(AIState.IDLE, Alignment.NEUTRAL),
        Activity(),
        Position(x=5, y=5, layer=0),
        Residence(hearth_pos=(12, 12), housed=True),
    )
    clock = MagicMock()
    clock.hour = 20
    container = _mock_map()
    schedule_system.process(clock, container)

    activity = esper.component_for_entity(ent, Activity)
    assert activity.target_pos == (12, 12), "hearth meta should resolve to the real campfire"


def test_full_schedule_lifecycle():
    # Setup
    esper.clear_database()
    schedule_system = ScheduleSystem()

    # 1. Register a schedule
    template_id = "villager_schedule"
    entries = [
        ScheduleEntry(start=6, end=18, activity="WORK", target_pos=(10, 10)),
        ScheduleEntry(start=18, end=22, activity="SOCIALIZE", target_pos=(20, 20)),
        ScheduleEntry(start=22, end=6, activity="SLEEP", target_pos=(5, 5)),
    ]
    template = ScheduleTemplate(id=template_id, name="Villager Schedule", entries=entries)
    schedule_registry.register(template)

    # 2. Create NPC with schedule
    # Note: EntityFactory would normally do this, but we're testing the system isolation
    ent = esper.create_entity(
        Schedule(schedule_id=template_id),
        AIBehaviorState(state=AIState.IDLE, alignment=Alignment.NEUTRAL),
        Activity(current_activity="IDLE", target_pos=None),
        Position(x=0, y=0, layer=0),
    )

    # 3. Mock dependencies
    world_clock = MagicMock()
    map_container = MagicMock()
    map_container.width = 30
    map_container.height = 30
    map_container.is_walkable.return_value = True

    # Mock Pathfinding to return a simple path
    PathfindingService.get_path = MagicMock(side_effect=lambda w, m, start, end, l: [(start[0] + 1, start[1] + 1), end])

    # --- TEST MORNING (WORK) ---
    world_clock.hour = 8
    schedule_system.process(world_clock, map_container)

    activity = esper.component_for_entity(ent, Activity)
    behavior = esper.component_for_entity(ent, AIBehaviorState)
    path = esper.component_for_entity(ent, PathData)

    print(f"Hour 8: Activity={activity.current_activity}, State={behavior.state}, Target={activity.target_pos}")
    assert activity.current_activity == "WORK"
    assert behavior.state == AIState.WORK
    assert activity.target_pos == (10, 10)
    assert path.destination == (10, 10)

    # --- TEST EVENING (SOCIALIZE) ---
    world_clock.hour = 19
    schedule_system.process(world_clock, map_container)

    activity = esper.component_for_entity(ent, Activity)
    behavior = esper.component_for_entity(ent, AIBehaviorState)
    path = esper.component_for_entity(ent, PathData)

    print(f"Hour 19: Activity={activity.current_activity}, State={behavior.state}, Target={activity.target_pos}")
    assert activity.current_activity == "SOCIALIZE"
    assert behavior.state == AIState.SOCIALIZE
    assert activity.target_pos == (20, 20)
    assert path.destination == (20, 20)

    # --- TEST NIGHT (SLEEP - Wrapping) ---
    world_clock.hour = 23
    schedule_system.process(world_clock, map_container)

    activity = esper.component_for_entity(ent, Activity)
    behavior = esper.component_for_entity(ent, AIBehaviorState)
    path = esper.component_for_entity(ent, PathData)

    print(f"Hour 23: Activity={activity.current_activity}, State={behavior.state}, Target={activity.target_pos}")
    assert activity.current_activity == "SLEEP"
    # Note: Still IDLE because NPC is not at (5, 5) yet
    assert behavior.state == AIState.IDLE
    assert activity.target_pos == (5, 5)

    # Move NPC to target_pos (5, 5)
    pos = esper.component_for_entity(ent, Position)
    pos.x, pos.y = 5, 5

    # Process again
    schedule_system.process(world_clock, map_container)
    behavior = esper.component_for_entity(ent, AIBehaviorState)
    assert behavior.state == AIState.SLEEP

    world_clock.hour = 2
    schedule_system.process(world_clock, map_container)
    activity = esper.component_for_entity(ent, Activity)
    print(f"Hour 2: Activity={activity.current_activity}")
    assert activity.current_activity == "SLEEP"

    print("Verification Successful!")


if __name__ == "__main__":
    test_full_schedule_lifecycle()

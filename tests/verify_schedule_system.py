import esper
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ecs.components import Schedule, AIBehaviorState, Activity, Position, AIState, Alignment, PathData
from ecs.systems.schedule_system import ScheduleSystem
from entities.schedule_registry import schedule_registry, ScheduleTemplate, ScheduleEntry
from services.pathfinding_service import PathfindingService

def test_full_schedule_lifecycle():
    # Setup
    esper.clear_database()
    schedule_system = ScheduleSystem()
    
    # 1. Register a schedule
    template_id = "villager_schedule"
    entries = [
        ScheduleEntry(start=6, end=18, activity="WORK", target_pos=(10, 10)),
        ScheduleEntry(start=18, end=22, activity="SOCIALIZE", target_pos=(20, 20)),
        ScheduleEntry(start=22, end=6, activity="SLEEP", target_pos=(5, 5))
    ]
    template = ScheduleTemplate(id=template_id, name="Villager Schedule", entries=entries)
    schedule_registry.register(template)
    
    # 2. Create NPC with schedule
    # Note: EntityFactory would normally do this, but we're testing the system isolation
    ent = esper.create_entity(
        Schedule(schedule_id=template_id),
        AIBehaviorState(state=AIState.IDLE, alignment=Alignment.NEUTRAL),
        Activity(current_activity="IDLE", target_pos=None),
        Position(x=0, y=0, layer=0)
    )
    
    # 3. Mock dependencies
    world_clock = MagicMock()
    map_container = MagicMock()
    map_container.width = 30
    map_container.height = 30
    map_container.is_walkable.return_value = True
    
    # Mock Pathfinding to return a simple path
    PathfindingService.get_path = MagicMock(side_effect=lambda w, m, start, end, l: [(start[0]+1, start[1]+1), end])
    
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

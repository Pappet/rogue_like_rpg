import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import esper

from game.components import Activity, AIBehaviorState, AIState, Alignment, Position, Schedule
from game.content.entity_registry import entity_registry
from game.content.resource_loader import ResourceLoader
from game.content.schedule_registry import schedule_registry
from game.services.world_simulation_service import resolve_scheduled_target


def test_mayor_schedule_within_bounds():
    # Clear and reload registries
    entity_registry.clear()
    schedule_registry.clear()

    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_entities("assets/data/entities.json")

    # Verify mayor template home_pos is within bounds of Brackenfen Manor (12x12)
    mayor_template = entity_registry.get("mayor")
    assert mayor_template is not None
    assert mayor_template.home_pos is not None

    # Brackenfen Manor is 12x12, so check coordinates are within 0..11
    hx, hy = mayor_template.home_pos
    assert 0 <= hx < 12, f"Mayor home_pos x={hx} is out of bounds for a 12x12 manor"
    assert 0 <= hy < 12, f"Mayor home_pos y={hy} is out of bounds for a 12x12 manor"

    # Verify mayor routine schedule entries do not point out of bounds
    routine = schedule_registry.get("mayor_routine")
    assert routine is not None

    world = esper
    # Create a dummy mayor entity to test schedule target resolution
    esper.clear_database()
    ent = world.create_entity(
        Position(0, 0, 0),
        Schedule("mayor_routine"),
        Activity(home_pos=mayor_template.home_pos),
        AIBehaviorState(state=AIState.IDLE, alignment=Alignment.NEUTRAL),
    )

    # Test resolved target for every hour of the day
    for hour in range(24):
        entry = routine.entry_for_hour(hour)
        assert entry is not None

        # Resolve target
        target = resolve_scheduled_target(entry, world.component_for_entity(ent, Activity), ent, world)

        # Verify target is within bounds of the 12x12 Brackenfen Manor
        if target is not None:
            tx, ty = target
            assert 0 <= tx < 12, f"Mayor target x={tx} at hour {hour} is out of bounds for a 12x12 manor"
            assert 0 <= ty < 12, f"Mayor target y={ty} at hour {hour} is out of bounds for a 12x12 manor"

        # Socialize activity should not target the hearth (which would resolve to the exterior campfire)
        if entry.activity.upper() == "SOCIALIZE":
            assert entry.target_meta != "hearth", "Mayor routine should not target hearth as he is an indoor NPC"


if __name__ == "__main__":
    test_mayor_schedule_within_bounds()
    print("Mayor schedule verification: SUCCESS")

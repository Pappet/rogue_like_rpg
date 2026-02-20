import esper
import sys
import os
from unittest.mock import MagicMock

# Ensure we can import from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.map_service import MapService
from services.resource_loader import ResourceLoader
from ecs.world import reset_world
from ecs.components import Position, AIBehaviorState, Alignment, Schedule, Activity, AIState, Name
from ecs.systems.schedule_system import ScheduleSystem
from entities.entity_registry import EntityRegistry
from map.tile_registry import TileRegistry
from entities.schedule_registry import schedule_registry

def test_village_population():
    print("Testing Village Population...")
    
    # Initialize world and systems
    reset_world()
    world = esper
    map_service = MapService()
    
    # Load registries
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_schedules("assets/data/schedules.json")
    
    # Create village scenario
    map_service.create_village_scenario(world)
    
    # 1. Verify entities in Village map
    village_map = map_service.get_map("Village")
    # Village should have 4 NPCs spawned (2 guards, 2 villagers) + portals
    # Plus player if it was there (but we haven't added player in this test)
    
    # Find entities in Village map
    # village_map.thaw(world) should have been called in create_village_scenario
    npcs = []
    for ent, (pos, name) in world.get_components(Position, Name):
        if pos.layer == 0:
             # Check if it's one of our NPCs
             if "Guard" in name.name or "Villager" in name.name:
                 npcs.append(ent)
    
    print(f"Found {len(npcs)} NPCs in Village map")
    assert len(npcs) == 4, f"Expected 4 NPCs in Village, found {len(npcs)}"
    
    # 2. Verify entities in House interiors
    shop_map = map_service.get_map("Shop")
    print(f"Shop frozen entities: {len(shop_map.frozen_entities)}")
    # Shop should have 1 shopkeeper + 1 portal (to Village)
    # Actually shopkeeper is frozen into the container.
    assert len(shop_map.frozen_entities) >= 1, "Shop should have at least 1 frozen entity (shopkeeper)"
    
    # 3. Check NPC components
    for ent in npcs:
        assert world.has_component(ent, AIBehaviorState)
        assert world.has_component(ent, Schedule)
        assert world.has_component(ent, Activity)
        
        ai_state = world.component_for_entity(ent, AIBehaviorState)
        assert ai_state.alignment == Alignment.NEUTRAL
        
    print("All Village NPCs have correct components and alignment.")
    
    # 4. Mock WorldClockService and run ScheduleSystem
    clock_mock = MagicMock()
    schedule_system = ScheduleSystem()
    
    # Find a guard
    guard_ent = None
    for ent, (name, pos) in world.get_components(Name, Position):
        if "Guard" in name.name:
            guard_ent = ent
            break
    
    assert guard_ent is not None, "Could not find a guard entity"
    
    activity = world.component_for_entity(guard_ent, Activity)
    ai_state = world.component_for_entity(guard_ent, AIBehaviorState)
    
    # Test 10:00 (WORK)
    clock_mock.hour = 10
    schedule_system.process(clock_mock, village_map)
    
    print(f"Guard activity at 10:00: {activity.current_activity}")
    assert activity.current_activity == "WORK"
    assert ai_state.state == AIState.WORK
    
    # Test 20:00 (SOCIALIZE)
    clock_mock.hour = 20
    schedule_system.process(clock_mock, village_map)
    
    print(f"Guard activity at 20:00: {activity.current_activity}")
    assert activity.current_activity == "SOCIALIZE"
    assert ai_state.state == AIState.SOCIALIZE
    
    # Test 02:00 (SLEEP)
    clock_mock.hour = 2
    # Reset position to home to trigger SLEEP state
    pos = world.component_for_entity(guard_ent, Position)
    pos.x, pos.y = activity.home_pos
    
    schedule_system.process(clock_mock, village_map)
    
    print(f"Guard activity at 02:00: {activity.current_activity}")
    assert activity.current_activity == "SLEEP"
    assert ai_state.state == AIState.SLEEP
    
    print("ScheduleSystem verification PASSED")

if __name__ == "__main__":
    test_village_population()

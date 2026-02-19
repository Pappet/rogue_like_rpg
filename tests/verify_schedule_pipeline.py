from ecs.world import get_world
from services.resource_loader import ResourceLoader
from entities.entity_factory import EntityFactory
from entities.entity_registry import EntityRegistry
from entities.schedule_registry import schedule_registry
from ecs.components import Schedule
import os

def test_pipeline():
    print("Initializing verification...")
    # Clear registries
    EntityRegistry.clear()
    schedule_registry.clear()
    
    # Load schedules
    print("Loading schedules from assets/data/schedules.json...")
    ResourceLoader.load_schedules("assets/data/schedules.json")
    assert schedule_registry.get("villager_routine") is not None
    print("✓ ScheduleRegistry has 'villager_routine'")
    
    # Load entities
    print("Loading entities from assets/data/entities.json...")
    ResourceLoader.load_entities("assets/data/entities.json")
    v_template = EntityRegistry.get("villager")
    assert v_template is not None
    assert v_template.schedule_id == "villager_routine"
    print("✓ EntityRegistry 'villager' template has schedule_id='villager_routine'")
    
    # Create entity
    print("Creating 'villager' entity via EntityFactory...")
    world = get_world()
    v_id = EntityFactory.create(world, "villager", 5, 5)
    
    schedule_comp = world.component_for_entity(v_id, Schedule)
    assert schedule_comp.schedule_id == "villager_routine"
    print(f"✓ Created entity {v_id} has Schedule component with id='villager_routine'")
    
    print("\nSchedule data pipeline verification: SUCCESS")

if __name__ == "__main__":
    test_pipeline()

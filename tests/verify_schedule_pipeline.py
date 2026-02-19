from ecs.world import get_world
from services.resource_loader import ResourceLoader
from entities.entity_factory import EntityFactory
from entities.entity_registry import EntityRegistry
from entities.schedule_registry import schedule_registry
import os

def test_pipeline():
    # Clear registries
    EntityRegistry.clear()
    schedule_registry.clear()
    
    # Files exist (verified by write_file)
    # Load schedules
    ResourceLoader.load_schedules("assets/data/schedules.json")
    assert schedule_registry.get("villager_routine") is not None
    
    # Load entities
    ResourceLoader.load_entities("assets/data/entities.json")
    v_template = EntityRegistry.get("villager")
    assert v_template is not None
    assert v_template.schedule_id == "villager_routine"
    
    # Create entity
    world = get_world()
    v_id = EntityFactory.create(world, "villager", 0, 0)
    
    from ecs.components import Schedule
    schedule_comp = world.component_for_entity(v_id, Schedule)
    assert schedule_comp.schedule_id == "villager_routine"
    
    print("Task 2 pipeline verified")

if __name__ == "__main__":
    test_pipeline()

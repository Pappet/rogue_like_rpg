import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import esper
from entities.item_factory import ItemFactory
from entities.item_registry import ItemRegistry, ItemTemplate
from ecs.components import Inventory, Position, Name, Portable
from services.party_service import get_entity_closure
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile

from ecs.world import get_world, reset_world

def test_item_persistence():
    print("Starting Item Persistence Test...")
    # 1. Setup
    reset_world()
    world = get_world()
    
    # Register a dummy item
    ItemRegistry.register(ItemTemplate(
        id="test_sword",
        name="Test Sword",
        sprite="/",
        color=(255, 255, 255),
        sprite_layer="ITEMS",
        weight=1.0,
        material="iron"
    ))
    
    # Create player
    player = world.create_entity(Name("Player"), Inventory())
    
    # Create an item on ground
    ground_item = ItemFactory.create_on_ground(world, "test_sword", 5, 5)
    
    # Create an item to be picked up
    carried_item = ItemFactory.create(world, "test_sword")
    inventory = world.component_for_entity(player, Inventory)
    inventory.items.append(carried_item)
    
    print(f"Initial state: Ground Item ID={ground_item}, Carried Item ID={carried_item}, Player ID={player}")
    
    # 2. Simulate Map Transition (Exit)
    # Create a dummy MapContainer
    width, height = 10, 10
    tiles = [[Tile() for _ in range(width)] for _ in range(height)]
    layer = MapLayer(tiles)
    map_container = MapContainer([layer])
    
    # Get closure
    closure = get_entity_closure(world, player)
    print(f"Closure: {closure}")
    assert player in closure, "Player must be in closure"
    assert carried_item in closure, "Carried item must be in closure"
    assert ground_item not in closure, "Ground item must NOT be in closure"
    
    # Freeze
    map_container.freeze(world, exclude_entities=closure)
    
    # Verify ground item is deleted from world
    assert not world.entity_exists(ground_item), "Ground item should be deleted from world"
    # Verify player and carried item still exist (same IDs)
    assert world.entity_exists(player), "Player should still exist"
    assert world.entity_exists(carried_item), "Carried item should still exist"
    
    # Verify carried item still has its components
    assert world.has_component(carried_item, Name), "Carried item should have Name"
    assert world.component_for_entity(carried_item, Name).name == "Test Sword"
    assert world.has_component(carried_item, Portable), "Carried item should have Portable"
    
    # 3. Simulate Transition back (thaw)
    # Thaw into the SAME world (simulating returning to a map)
    map_container.thaw(world)
    
    # Find the thawed ground item
    thawed_ground_item = None
    for ent, (name, pos) in world.get_components(Name, Position):
        if name.name == "Test Sword" and ent != carried_item:
            thawed_ground_item = ent
            break
    
    assert thawed_ground_item is not None, "Ground item should be thawed"
    assert thawed_ground_item != ground_item, "Thawed item should have a new ID (unless esper reused it)"
    assert world.has_component(thawed_ground_item, Position)
    pos = world.component_for_entity(thawed_ground_item, Position)
    assert pos.x == 5 and pos.y == 5, f"Thawed item position mismatch: {pos.x}, {pos.y}"
    
    # Verify carried item is STILL in inventory and has same ID
    inventory = world.component_for_entity(player, Inventory)
    assert carried_item in inventory.items, "Carried item ID should still be in player inventory"
    assert world.entity_exists(carried_item), "Carried item should still exist after thaw"
    
    print("Item Persistence Test PASSED!")

if __name__ == "__main__":
    try:
        test_item_persistence()
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

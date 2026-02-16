import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import esper
from ecs.world import get_world, reset_world
from ecs.systems.death_system import DeathSystem
from ecs.components import Position, LootTable, Name, Blocker
from entities.item_registry import ItemRegistry, ItemTemplate
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile

class MockMap:
    def __init__(self, walkable_mask):
        self.walkable_mask = walkable_mask
        self.width = len(walkable_mask[0])
        self.height = len(walkable_mask)

    def is_walkable(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.walkable_mask[y][x]
        return False

def test_loot_drop_guaranteed():
    print("Testing guaranteed loot drop...")
    reset_world()
    world = get_world()
    
    death_system = DeathSystem()
    world.add_processor(death_system)
    
    # Register test item
    ItemRegistry.clear()
    ItemRegistry.register(ItemTemplate(
        id="test_item", name="Test Item", sprite="i", color=(255,255,255),
        sprite_layer="ITEMS", weight=1.0, material="gold"
    ))
    
    # Create mock map (all walkable)
    mock_map = MockMap([[True, True, True], [True, True, True], [True, True, True]])
    death_system.set_map(mock_map)
    
    # Create monster with guaranteed drop
    monster = world.create_entity(
        Position(1, 1),
        LootTable(entries=[("test_item", 1.0)]),
        Name("Monster")
    )
    
    # Trigger death
    esper.dispatch_event("entity_died", monster)
    
    # Verify item spawned at (1, 1)
    found = False
    for ent, (pos, name) in world.get_components(Position, Name):
        if name.name == "Test Item" and pos.x == 1 and pos.y == 1:
            found = True
            break
    
    assert found, "Item should have dropped at (1, 1)"
    print("Guaranteed loot drop test PASSED!")

def test_loot_scattering():
    print("Testing loot scattering when center is blocked...")
    reset_world()
    world = get_world()
    
    death_system = DeathSystem()
    world.add_processor(death_system)
    
    # Register test item
    ItemRegistry.clear()
    ItemRegistry.register(ItemTemplate(
        id="test_item", name="Test Item", sprite="i", color=(255,255,255),
        sprite_layer="ITEMS", weight=1.0, material="gold"
    ))
    
    # Create mock map (center (1,1) is NOT walkable)
    mock_map = MockMap([
        [True, True, True],
        [True, False, True],
        [True, True, True]
    ])
    death_system.set_map(mock_map)
    
    # Create monster with guaranteed drop at (1, 1)
    monster = world.create_entity(
        Position(1, 1),
        LootTable(entries=[("test_item", 1.0)]),
        Name("Monster")
    )
    
    # Trigger death
    esper.dispatch_event("entity_died", monster)
    
    # Verify item spawned at a walkable neighbor
    found = False
    drop_pos = None
    for ent, (pos, name) in world.get_components(Position, Name):
        if name.name == "Test Item":
            found = True
            drop_pos = (pos.x, pos.y)
            break
    
    assert found, "Item should have dropped"
    assert drop_pos != (1, 1), "Item should NOT have dropped at blocked (1, 1)"
    assert mock_map.is_walkable(drop_pos[0], drop_pos[1]), f"Item dropped at non-walkable position {drop_pos}"
    
    print(f"Loot scattered to {drop_pos}. Test PASSED!")

if __name__ == "__main__":
    try:
        test_loot_drop_guaranteed()
        test_loot_scattering()
        print("All loot system tests PASSED!")
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

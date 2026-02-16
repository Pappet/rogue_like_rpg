import sys
import os
import esper

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ecs.world import reset_world
from ecs.components import Position, Portable, Inventory, Stats, Name, Renderable
from config import SpriteLayer

def test_inventory_logic():
    reset_world()
    
    # 1. Setup Player
    player = esper.create_entity()
    esper.add_component(player, Position(x=1, y=1, layer=0))
    esper.add_component(player, Inventory())
    esper.add_component(player, Stats(hp=10, max_hp=10, power=5, defense=5, mana=10, max_mana=10, perception=5, intelligence=5, max_carry_weight=10.0))
    
    # 2. Setup Item
    item1 = esper.create_entity()
    esper.add_component(item1, Position(x=1, y=1, layer=0))
    esper.add_component(item1, Portable(weight=5.0))
    esper.add_component(item1, Name(name="Light Item"))
    esper.add_component(item1, Renderable(sprite="item", layer=SpriteLayer.ITEMS.value))
    
    item2 = esper.create_entity()
    esper.add_component(item2, Position(x=1, y=1, layer=0))
    esper.add_component(item2, Portable(weight=6.0))
    esper.add_component(item2, Name(name="Heavy Item"))
    
    print("Testing Pickup...")
    
    # Simulate pickup_item logic from game_states.py
    def pickup(player_ent, item_ent):
        player_pos = esper.component_for_entity(player_ent, Position)
        inventory = esper.component_for_entity(player_ent, Inventory)
        stats = esper.component_for_entity(player_ent, Stats)
        portable = esper.component_for_entity(item_ent, Portable)
        
        # Weight check
        current_weight = sum(esper.component_for_entity(i, Portable).weight for i in inventory.items)
        if current_weight + portable.weight > stats.max_carry_weight:
            return False
            
        # Move to inventory
        esper.remove_component(item_ent, Position)
        inventory.items.append(item_ent)
        return True

    # Pickup first item
    success = pickup(player, item1)
    assert success is True
    assert item1 in esper.component_for_entity(player, Inventory).items
    assert not esper.has_component(item1, Position)
    print("✓ Successfully picked up item1")

    # Try to pickup second item (exceeds weight)
    success = pickup(player, item2)
    assert success is False
    assert item2 not in esper.component_for_entity(player, Inventory).items
    assert esper.has_component(item2, Position)
    print("✓ Correctly rejected item2 due to weight limit")

    print("Testing Drop...")
    
    # Simulate drop_item logic from game_states.py
    def drop(player_ent, item_idx):
        inventory = esper.component_for_entity(player_ent, Inventory)
        item_ent = inventory.items.pop(item_idx)
        player_pos = esper.component_for_entity(player_ent, Position)
        
        esper.add_component(item_ent, Position(player_pos.x, player_pos.y, player_pos.layer))
        
        if esper.has_component(item_ent, Renderable):
            esper.component_for_entity(item_ent, Renderable).layer = SpriteLayer.ITEMS.value
            
        return item_ent

    # Drop first item
    dropped_item = drop(player, 0)
    assert dropped_item == item1
    assert item1 not in esper.component_for_entity(player, Inventory).items
    assert esper.has_component(item1, Position)
    pos = esper.component_for_entity(item1, Position)
    assert pos.x == 1 and pos.y == 1
    assert esper.component_for_entity(item1, Renderable).layer == SpriteLayer.ITEMS.value
    print("✓ Successfully dropped item1")

    print("\nAll Inventory Logic Tests Passed!")

if __name__ == "__main__":
    test_inventory_logic()

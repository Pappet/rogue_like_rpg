import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import esper
from ecs.world import get_world, reset_world
from ecs.systems.action_system import ActionSystem
from ecs.systems.turn_system import TurnSystem
from ecs.components import Position, Name, Description, ItemMaterial, Portable, Action, Targeting, Stats
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile, VisibilityState

def test_inspection_output_detailed():
    print("Testing detailed inspection output...")
    reset_world()
    world = get_world()
    
    # Mock map with one visible tile
    tile = Tile(transparent=True)
    tile.visibility_state = VisibilityState.VISIBLE
    layer = MapLayer([[tile]])
    map_container = MapContainer([layer])
    
    turn_system = TurnSystem()
    action_system = ActionSystem(map_container, turn_system)
    
    # Create an item
    item = world.create_entity(
        Position(0, 0),
        Name("Healing Potion"),
        Description("A bubbly red liquid."),
        ItemMaterial("glass"),
        Portable(0.5)
    )
    
    # Capture log messages
    messages = []
    def capture_handler(msg, *args):
        messages.append(msg)
    esper.set_handler("log_message", capture_handler)
    
    # Simulate inspection
    player = world.create_entity(
        Position(0, 0),
        Stats(hp=10, max_hp=10, power=5, defense=2, mana=10, max_mana=10,
              perception=5, intelligence=5),
    )
    targeting_action = Action("Inspect", targeting_mode="inspect", range=5)
    
    # We need to set targeting component
    targeting = Targeting(
        origin_x=0, origin_y=0, target_x=0, target_y=0,
        range=5, mode="inspect", action=targeting_action
    )
    world.add_component(player, targeting)
    
    # Confirm action (which triggers inspection output)
    action_system.confirm_action(player)
    
    # Check messages
    print("Captured messages:")
    for m in messages:
        print(f"  - {m}")
        
    # Expected messages:
    # 1. Tile name (from registry, but since it's mock it might be "Unknown tile")
    # 2. Entity name in yellow: [color=yellow]Healing Potion[/color]
    # 3. Detailed description: A bubbly red liquid.
    # Material: glass
    # Weight: 0.5kg
    
    found_name = any("[color=yellow]Healing Potion[/color]" in m for m in messages)
    found_desc = any("A bubbly red liquid." in m and "Material: glass" in m and "Weight: 0.5kg" in m for m in messages)
    
    assert found_name, "Item name should be in yellow"
    assert found_desc, "Detailed description should contain all parts"
    
    print("Detailed inspection output test PASSED!")

if __name__ == "__main__":
    try:
        test_inspection_output_detailed()
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

import sys
import os
import esper

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ecs.components import Position, Stats, EffectiveStats, TurnOrder
from ecs.systems.equipment_system import EquipmentSystem
from ecs.systems.visibility_system import VisibilitySystem
from ecs.systems.turn_system import TurnSystem
from services.world_clock_service import WorldClockService
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile, VisibilityState
from config import TICKS_PER_HOUR, DAY_START, NIGHT_START, SpriteLayer

def setup_test_world():
    esper.clear_database()
    world_clock = WorldClockService(total_ticks=DAY_START * TICKS_PER_HOUR) # Start at Day
    
    # Create a simple 20x20 map
    tiles = [[Tile(transparent=True, sprites={SpriteLayer.GROUND: "."}) for _ in range(20)] for _ in range(20)]
    layer = MapLayer(tiles)
    map_container = MapContainer([layer])
    
    turn_system = TurnSystem(world_clock)
    equipment_system = EquipmentSystem(world_clock)
    visibility_system = VisibilitySystem(map_container, turn_system)
    
    esper.add_processor(turn_system)
    esper.add_processor(equipment_system)
    esper.add_processor(visibility_system)
    
    # Create player
    player = esper.create_entity(
        Position(10, 10, 0),
        Stats(
            hp=20, max_hp=20, power=5, defense=5, mana=10, max_mana=10,
            perception=10, intelligence=10,
            base_hp=20, base_max_hp=20, base_power=5, base_defense=5,
            base_mana=10, base_max_mana=10, base_perception=10, base_intelligence=10
        ),
        TurnOrder(0)
    )
    
    return world_clock, equipment_system, visibility_system, player, map_container

def test_day_night_perception():
    print("Testing Day/Night perception changes...")
    world_clock, equip_sys, vis_sys, player, map_container = setup_test_world()
    
    # 1. Verify Day perception
    # We need to run equipment system once to generate EffectiveStats
    equip_sys.process()
    
    eff_stats = esper.component_for_entity(player, EffectiveStats)
    print(f"Day phase: {world_clock.phase}, Perception: {eff_stats.perception}")
    assert world_clock.phase == "day"
    assert eff_stats.perception == 10
    
    # 2. Advance to Night
    world_clock.total_ticks = NIGHT_START * TICKS_PER_HOUR
    print(f"Advanced to hour: {world_clock.hour}, phase: {world_clock.phase}")
    assert world_clock.phase == "night"
    
    # 3. Run EquipmentSystem and verify perception reduced
    equip_sys.process()
    eff_stats = esper.component_for_entity(player, EffectiveStats)
    print(f"Night Perception: {eff_stats.perception}")
    # Night multiplier is 0.5. 10 * 0.5 = 5
    assert eff_stats.perception == 5
    
    # 4. Run VisibilitySystem and check if it uses the new perception
    vis_sys.process()
    
    # At (10,10) with radius 5:
    # (15, 10) should be visible (distance 5)
    # (16, 10) should NOT be visible (distance 6)
    
    tile_15_10 = map_container.get_tile(15, 10, 0)
    tile_16_10 = map_container.get_tile(16, 10, 0)
    
    print(f"Tile (15,10) visibility: {tile_15_10.visibility_state}")
    print(f"Tile (16,10) visibility: {tile_16_10.visibility_state}")
    
    assert tile_15_10.visibility_state == VisibilityState.VISIBLE
    assert tile_16_10.visibility_state != VisibilityState.VISIBLE
    
    # 5. Advance to Day again
    world_clock.total_ticks = (24 + DAY_START) * TICKS_PER_HOUR
    equip_sys.process()
    eff_stats = esper.component_for_entity(player, EffectiveStats)
    print(f"Back to Day Perception: {eff_stats.perception}")
    assert eff_stats.perception == 10
    
    # 6. Run VisibilitySystem and check if FOV restored
    vis_sys.process()
    tile_16_10 = map_container.get_tile(16, 10, 0)
    print(f"Back to Day: Tile (16,10) visibility: {tile_16_10.visibility_state}")
    assert tile_16_10.visibility_state == VisibilityState.VISIBLE
    
    print("test_day_night_perception PASSED")

def test_perception_floor():
    print("Testing perception floor (never below 1)...")
    world_clock, equip_sys, vis_sys, player, map_container = setup_test_world()
    
    # Set base perception to 1
    stats = esper.component_for_entity(player, Stats)
    stats.base_perception = 1
    
    # Go to Night (multiplier 0.5)
    world_clock.total_ticks = NIGHT_START * TICKS_PER_HOUR
    equip_sys.process()
    
    eff_stats = esper.component_for_entity(player, EffectiveStats)
    print(f"Night Perception (base 1): {eff_stats.perception}")
    assert eff_stats.perception == 1
    
    print("test_perception_floor PASSED")

if __name__ == "__main__":
    try:
        test_day_night_perception()
        test_perception_floor()
        print("\nALL TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

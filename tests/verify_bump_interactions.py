import sys
import os

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import esper
from ecs.components import Position, MovementRequest, AIBehaviorState, AIState, Alignment, Stats, Name, AttackIntent, Blocker
from ecs.systems.movement_system import MovementSystem
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile
from config import SpriteLayer

# Mock ActionSystem
class MockActionSystem:
    def __init__(self):
        self.woken_up = None

    def wake_up(self, ent):
        self.woken_up = ent

def test_bump_attack():
    esper.clear_database()
    
    # Mock map - make it walkable
    tiles = [[Tile() for _ in range(10)] for _ in range(10)]
    for row in tiles:
        for tile in row:
            tile.sprites = {SpriteLayer.GROUND: "."}
            
    layer = MapLayer(tiles)
    m = MapContainer([layer])
            
    action_system = MockActionSystem()
    movement_system = MovementSystem(m, action_system)
    
    # Player
    player = esper.create_entity(Position(1, 1), MovementRequest(1, 0))
    # Hostile monster at (2, 1)
    monster = esper.create_entity(
        Position(2, 1), 
        AIBehaviorState(AIState.IDLE, Alignment.HOSTILE), 
        Stats(10,10,5,5,5,5,1,1), 
        Name("Monster"),
        Blocker()
    )
    
    movement_system.process()
    
    # Check if player still at (1, 1) and has AttackIntent
    pos = esper.component_for_entity(player, Position)
    assert pos.x == 1 and pos.y == 1
    assert esper.has_component(player, AttackIntent)
    assert esper.component_for_entity(player, AttackIntent).target_entity == monster
    print("Bump Attack test passed!")

def test_bump_wake_up():
    esper.clear_database()
    
    # Mock map - make it walkable
    tiles = [[Tile() for _ in range(10)] for _ in range(10)]
    for row in tiles:
        for tile in row:
            tile.sprites = {SpriteLayer.GROUND: "."}
            
    layer = MapLayer(tiles)
    m = MapContainer([layer])
            
    action_system = MockActionSystem()
    movement_system = MovementSystem(m, action_system)
    
    # Player
    player = esper.create_entity(Position(1, 1), MovementRequest(1, 0))
    # Sleeping villager at (2, 1)
    villager = esper.create_entity(
        Position(2, 1), 
        AIBehaviorState(AIState.SLEEP, Alignment.NEUTRAL), 
        Name("Villager"),
        Blocker()
    )
    
    movement_system.process()
    
    # Check if action_system.wake_up was called
    assert action_system.woken_up == villager
    print("Bump Wake Up test passed!")

if __name__ == "__main__":
    test_bump_attack()
    test_bump_wake_up()

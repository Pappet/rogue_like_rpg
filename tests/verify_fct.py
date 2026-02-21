import esper
import pygame
import time
from ecs.components import Position, Stats, Name, FCT, AttackIntent
from ecs.systems.combat_system import CombatSystem
from ecs.systems.fct_system import FCTSystem

def test_fct():
    # Initialize esper world
    esper.clear_database()
    
    # Initialize systems
    combat_system = CombatSystem()
    fct_system = FCTSystem()
    esper.add_processor(combat_system)
    esper.add_processor(fct_system)
    
    # Create attacker
    attacker = esper.create_entity(
        Name("Attacker"),
        Stats(hp=10, max_hp=10, power=5, defense=0, mana=0, max_mana=0, perception=5, intelligence=5)
    )
    
    # Create target
    target = esper.create_entity(
        Name("Target"),
        Position(5, 5),
        Stats(hp=10, max_hp=10, power=2, defense=2, mana=0, max_mana=0, perception=5, intelligence=5)
    )
    
    print(f"Initial target HP: {esper.component_for_entity(target, Stats).hp}")
    
    # 1. Trigger Attack
    esper.add_component(attacker, AttackIntent(target))
    
    # 2. Process Combat
    esper.process(0.016) # Simulate 1 frame
    
    print(f"Target HP after attack: {esper.component_for_entity(target, Stats).hp}")
    
    # 3. Check for FCT entity
    fcts = esper.get_component(FCT)
    if not fcts:
        print("FAIL: No FCT entity created")
        return
    
    ent, fct = fcts[0]
    print(f"FCT created: text={fct.text}, pos=({esper.component_for_entity(ent, Position).x}, {esper.component_for_entity(ent, Position).y})")
    
    # 4. Process FCT lifecycle
    initial_offset_y = fct.offset_y
    esper.process(0.1) # Simulate 100ms
    
    fct = esper.component_for_entity(ent, FCT)
    print(f"FCT after 100ms: offset_y={fct.offset_y}, ttl={fct.ttl}")
    
    if fct.offset_y >= initial_offset_y:
        print("FAIL: FCT did not move upwards (vy is negative, so offset_y should decrease)")
    else:
        print("SUCCESS: FCT moved upwards")
        
    # 5. Fast forward to expiration
    esper.process(1.0)
    
    if esper.entity_exists(ent):
        print(f"FAIL: FCT entity still exists after TTL (ttl={esper.component_for_entity(ent, FCT).ttl})")
    else:
        print("SUCCESS: FCT entity deleted after TTL")

if __name__ == "__main__":
    test_fct()

import esper
from unittest.mock import MagicMock
from ecs.components import Stats, Equipment, EffectiveStats, StatModifiers, Equippable, SlotType, Name, AttackIntent
from ecs.systems.equipment_system import EquipmentSystem
from ecs.systems.combat_system import CombatSystem
from services.equipment_service import equip_item

def test_combat_with_equipment():
    # Setup world and systems
    esper.clear_database()
    # Order: Equipment before Combat
    esper.add_processor(EquipmentSystem(MagicMock()))
    esper.add_processor(CombatSystem())
    
    # Create attacker (player)
    attacker = esper.create_entity()
    esper.add_component(attacker, Name(name="Player"))
    esper.add_component(attacker, Stats(
        hp=10, max_hp=10, power=2, defense=1, mana=5, max_mana=5,
        perception=5, intelligence=5,
        base_max_hp=10, base_power=2, base_defense=1, base_mana=5,
        base_max_mana=5, base_perception=5, base_intelligence=5
    ))
    esper.add_component(attacker, Equipment())
    
    # Create target (monster)
    target = esper.create_entity()
    esper.add_component(target, Name(name="Monster"))
    target_stats = Stats(
        hp=20, max_hp=20, power=2, defense=1, mana=5, max_mana=5,
        perception=5, intelligence=5,
        base_max_hp=20, base_power=2, base_defense=1, base_mana=5,
        base_max_mana=5, base_perception=5, base_intelligence=5
    )
    esper.add_component(target, target_stats)
    
    # Attack without sword: 2 power - 1 defense = 1 damage
    esper.add_component(attacker, AttackIntent(target_entity=target))
    esper.process()
    
    assert target_stats.hp == 19
    print(f"Damage without sword: 1 (HP: {target_stats.hp})")
    
    # Equip sword (+5 power)
    sword = esper.create_entity()
    esper.add_component(sword, Equippable(slot=SlotType.MAIN_HAND))
    esper.add_component(sword, StatModifiers(power=5))
    equip_item(esper, attacker, sword)
    
    # Attack with sword: (2+5) power - 1 defense = 6 damage
    esper.add_component(attacker, AttackIntent(target_entity=target))
    esper.process()
    
    # 19 - 6 = 13
    assert target_stats.hp == 13
    print(f"Damage with sword: 6 (HP: {target_stats.hp})")

    # Cleanup
    esper.remove_processor(EquipmentSystem)
    esper.remove_processor(CombatSystem)

if __name__ == "__main__":
    try:
        test_combat_with_equipment()
        print("Combat integration verification passed!")
    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

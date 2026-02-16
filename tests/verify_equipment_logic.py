import esper
from ecs.components import Stats, Equipment, EffectiveStats, StatModifiers, Equippable, SlotType, Name
from ecs.systems.equipment_system import EquipmentSystem
from services.equipment_service import equip_item

def test_equipment_calculation():
    # Setup world and systems
    esper.clear_database()
    # In esper 3.x, processors are added to the global state
    system = EquipmentSystem()
    esper.add_processor(system)
    
    # Create player
    player = esper.create_entity()
    stats = Stats(
        hp=10, max_hp=10, power=2, defense=1, mana=5, max_mana=5,
        perception=5, intelligence=5,
        base_max_hp=10, base_power=2, base_defense=1, base_mana=5,
        base_max_mana=5, base_perception=5, base_intelligence=5
    )
    equipment = Equipment()
    esper.add_component(player, stats)
    esper.add_component(player, equipment)
    
    # Create item
    item = esper.create_entity()
    esper.add_component(item, Name(name="Sword"))
    esper.add_component(item, Equippable(slot=SlotType.MAIN_HAND))
    esper.add_component(item, StatModifiers(power=5))
    
    # Process once - should have base stats
    esper.process()
    eff = esper.component_for_entity(player, EffectiveStats)
    assert eff.power == 2
    print("Base power verified.")
    
    # Equip item
    equip_item(esper, player, item)
    assert equipment.slots[SlotType.MAIN_HAND] == item
    
    # Process - should have updated stats
    esper.process()
    eff = esper.component_for_entity(player, EffectiveStats)
    assert eff.power == 7
    print("Equipped power verified (2 + 5 = 7).")
    
    # Unequip item
    equip_item(esper, player, item)
    assert equipment.slots[SlotType.MAIN_HAND] is None
    
    # Process - should have base stats again
    esper.process()
    eff = esper.component_for_entity(player, EffectiveStats)
    assert eff.power == 2
    print("Unequipped power verified (back to 2).")
    
    # Cleanup
    esper.remove_processor(EquipmentSystem)

if __name__ == "__main__":
    try:
        test_equipment_calculation()
        print("Equipment logic verification passed!")
    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

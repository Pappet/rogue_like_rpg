from ecs.world import get_world, reset_world
from ecs.components import Equippable, SlotType, Equipment, EffectiveStats, StatModifiers
from entities.item_registry import ItemRegistry, ItemTemplate
from entities.item_factory import ItemFactory

def test_equipment_components():
    print("Testing equipment components...")
    world = get_world()
    
    # Test SlotType
    assert SlotType.HEAD == "head"
    assert SlotType.MAIN_HAND == "main_hand"
    print("SlotType enum OK.")
    
    # Test Equippable
    eq = Equippable(slot=SlotType.HEAD)
    assert eq.slot == SlotType.HEAD
    print("Equippable component OK.")
    
    # Test Equipment
    equipment = Equipment()
    assert len(equipment.slots) == len(SlotType)
    assert equipment.slots[SlotType.HEAD] is None
    print("Equipment component OK.")
    
    # Test EffectiveStats
    eff = EffectiveStats(hp=10, max_hp=10, power=5, defense=2, mana=0, max_mana=0, perception=5, intelligence=5)
    assert eff.hp == 10
    assert eff.power == 5
    print("EffectiveStats component OK.")

def test_item_factory_with_slot():
    print("\nTesting ItemFactory with slots...")
    reset_world()
    world = get_world()
    ItemRegistry.clear()
    
    template = ItemTemplate(
        id="iron_helmet",
        name="Iron Helmet",
        sprite="[",
        color=(200, 200, 200),
        sprite_layer="ITEMS",
        weight=2.0,
        material="iron",
        slot="head",
        stats={"defense": 2}
    )
    ItemRegistry.register(template)
    
    item_entity = ItemFactory.create(world, "iron_helmet")
    
    # Verify Equippable component
    equippable = world.component_for_entity(item_entity, Equippable)
    assert equippable is not None
    assert equippable.slot == SlotType.HEAD
    print(f"Item created with Equippable component: {equippable}")
    
    # Verify StatModifiers component
    mods = world.component_for_entity(item_entity, StatModifiers)
    assert mods is not None
    assert mods.defense == 2
    print(f"Item created with StatModifiers component: {mods}")

    # Test item without slot
    template_no_slot = ItemTemplate(
        id="apple",
        name="Apple",
        sprite="%",
        color=(255, 0, 0),
        sprite_layer="ITEMS",
        weight=0.1,
        material="organic",
        stats={"hp": 5}
    )
    ItemRegistry.register(template_no_slot)
    apple_entity = ItemFactory.create(world, "apple")
    
    has_equippable = world.has_component(apple_entity, Equippable)
    assert not has_equippable
    print("Item without slot created correctly (no Equippable component).")

if __name__ == "__main__":
    try:
        test_equipment_components()
        test_item_factory_with_slot()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTests failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

import esper
from ecs.components import Equippable, Equipment, Name, SlotType

def equip_item(world, entity, item_id):
    """
    Equips an item to the entity. Toggles if already equipped.
    Handles unequipping the previous item in the same slot.
    """
    if not world.has_component(item_id, Equippable):
        return

    equippable = world.component_for_entity(item_id, Equippable)
    slot = equippable.slot
    
    if not world.has_component(entity, Equipment):
        return
        
    equipment = world.component_for_entity(entity, Equipment)
    item_name = world.component_for_entity(item_id, Name).name if world.has_component(item_id, Name) else "item"

    # Check if already equipped in THIS slot
    if equipment.slots.get(slot) == item_id:
        unequip_item(world, entity, slot)
    else:
        # If something else is in the slot, unequip it
        if equipment.slots.get(slot) is not None:
            old_item_id = equipment.slots[slot]
            old_item_name = world.component_for_entity(old_item_id, Name).name if world.has_component(old_item_id, Name) else "item"
            esper.dispatch_event("log_message", f"You unequip the {old_item_name}.")
            
        equipment.slots[slot] = item_id
        esper.dispatch_event("log_message", f"You equip the {item_name}.")

def unequip_item(world, entity, slot):
    """
    Unequips whatever is in the specified slot.
    """
    if not world.has_component(entity, Equipment):
        return
        
    equipment = world.component_for_entity(entity, Equipment)
    if equipment.slots.get(slot) is not None:
        item_id = equipment.slots[slot]
        item_name = world.component_for_entity(item_id, Name).name if world.has_component(item_id, Name) else "item"
        equipment.slots[slot] = None
        esper.dispatch_event("log_message", f"You unequip the {item_name}.")

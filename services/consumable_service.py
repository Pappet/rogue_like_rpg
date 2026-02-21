import esper
from ecs.components import Consumable, Stats, EffectiveStats, Inventory, Name, PlayerTag
from config import LogCategory

class ConsumableService:
    @staticmethod
    def use_item(world, user_ent, item_ent) -> bool:
        """Attempt to use a consumable item.
        
        Returns True if the item was used (and possibly consumed), 
        False if it couldn't be used (e.g. at full health).
        """
        if not world.has_component(item_ent, Consumable):
            return False
            
        consumable = world.component_for_entity(item_ent, Consumable)
        
        stats = world.component_for_entity(user_ent, Stats)
        eff = world.component_for_entity(user_ent, EffectiveStats) if world.has_component(user_ent, EffectiveStats) else None
        item_name = world.component_for_entity(item_ent, Name).name if world.has_component(item_ent, Name) else "item"
        
        # Determine current and max HP
        current_hp = eff.hp if eff else stats.hp
        max_hp = eff.max_hp if eff else stats.max_hp
        
        if consumable.effect_type == "heal_hp":
            if current_hp >= max_hp:
                esper.dispatch_event("log_message", "You are already at full health.")
                return False
                
            heal_amt = min(consumable.amount, max_hp - current_hp)
            stats.hp += heal_amt
            
            # If we have EffectiveStats, we should update it immediately too 
            # to remain consistent with the CombatSystem pattern
            if eff:
                eff.hp = stats.hp
                
            category = LogCategory.HEALING if esper.has_component(user_ent, PlayerTag) else LogCategory.SYSTEM
            esper.dispatch_event("log_message", f"You drink the {item_name}. (+{heal_amt} HP)", None, category)
            
        # Add more effect types here as needed
        
        # Consume the item
        if consumable.consumed_on_use:
            if world.has_component(user_ent, Inventory):
                inventory = world.component_for_entity(user_ent, Inventory)
                if item_ent in inventory.items:
                    inventory.items.remove(item_ent)
            
            world.delete_entity(item_ent)
            
        return True

import esper
from ecs.components import Stats, EffectiveStats, AttackIntent, Name

class CombatSystem(esper.Processor):
    def __init__(self, action_system=None):
        super().__init__()
        self.action_system = action_system

    def process(self):
        for attacker, intent in list(esper.get_component(AttackIntent)):
            target = intent.target_entity
            
            try:
                # Use EffectiveStats for calculations if available, fall back to base Stats
                attacker_eff = esper.try_component(attacker, EffectiveStats) or esper.component_for_entity(attacker, Stats)
                target_eff = esper.try_component(target, EffectiveStats) or esper.component_for_entity(target, Stats)
                
                # Base Stats component is still needed for persistent HP modification
                target_stats = esper.component_for_entity(target, Stats)
                
                # Calculate damage using effective values
                damage = max(0, attacker_eff.power - target_eff.defense)
                
                # Subtract HP from the base stats
                target_stats.hp -= damage
                
                # Update effective HP to avoid stale death check if it's a separate component
                if target_eff is not target_stats:
                    target_eff.hp -= damage
                
                # Wake up target if sleeping
                from ecs.components import AIBehaviorState, AIState
                if self.action_system and esper.has_component(target, AIBehaviorState):
                    self.action_system.wake_up(target)
                
                # Get names for logging
                attacker_name = self._get_name(attacker)
                target_name = self._get_name(target)
                
                # Dispatch log message
                if damage > 0:
                    esper.dispatch_event("log_message", f"{attacker_name} hits {target_name} for {damage} damage.")
                else:
                    esper.dispatch_event("log_message", f"{attacker_name} attacks {target_name} but deals no damage.")
                
                # Death Check
                # Use effective HP for death check to account for bonuses
                if target_eff.hp <= 0:
                    esper.dispatch_event("entity_died", target)
                
            except KeyError:
                # One of the entities might not have stats
                pass
            
            # Remove AttackIntent
            esper.remove_component(attacker, AttackIntent)

    def _get_name(self, entity):
        try:
            return esper.component_for_entity(entity, Name).name
        except KeyError:
            return f"Entity {entity}"

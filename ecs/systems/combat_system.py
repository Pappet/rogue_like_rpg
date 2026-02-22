import esper
import random
from ecs.components import Stats, EffectiveStats, AttackIntent, Name, Position, FCT, PlayerTag, MapBound, AIBehaviorState, AIState
from config import LogCategory

class CombatSystem(esper.Processor):
    def __init__(self, action_system=None):
        super().__init__()
        self.action_system = action_system

    def process(self, *args, **kwargs):
        for attacker, intent in list(esper.get_component(AttackIntent)):
            target = intent.target_entity
            
            attacker_stats = esper.try_component(attacker, Stats)
            target_stats = esper.try_component(target, Stats)
            
            if attacker_stats and target_stats:
                # Use EffectiveStats for calculations if available, fall back to base Stats
                attacker_eff = esper.try_component(attacker, EffectiveStats) or attacker_stats
                target_eff = esper.try_component(target, EffectiveStats) or target_stats
                
                # Calculate damage using effective values
                damage = max(0, attacker_eff.power - target_eff.defense)
                
                # Subtract HP from the base stats
                target_stats.hp -= damage
                
                # Update effective HP to avoid stale death check if it's a separate component
                if target_eff is not target_stats:
                    target_eff.hp -= damage
                
                # Wake up target if sleeping
                if self.action_system and esper.has_component(target, AIBehaviorState):
                    self.action_system.wake_up(target)
                
                # Get names for logging
                attacker_name = self._get_name(attacker)
                target_name = self._get_name(target)
                
                # Determine log category
                category = LogCategory.SYSTEM
                if esper.has_component(attacker, PlayerTag):
                    category = LogCategory.DAMAGE_DEALT
                elif esper.has_component(target, PlayerTag):
                    category = LogCategory.DAMAGE_RECEIVED

                # Dispatch log message
                if damage > 0:
                    esper.dispatch_event("log_message", f"{attacker_name} hits {target_name} for {damage} damage.", None, category)
                    self._spawn_fct(target, str(damage), (255, 0, 0))
                else:
                    esper.dispatch_event("log_message", f"{attacker_name} attacks {target_name} but deals no damage.", None, category)
                    self._spawn_fct(target, "0", (200, 200, 200))
                
                # Death Check
                # Use effective HP for death check to account for bonuses
                if target_eff.hp <= 0:
                    esper.dispatch_event("entity_died", target)
            
            # Remove AttackIntent
            esper.remove_component(attacker, AttackIntent)

    def _spawn_fct(self, target_entity, text, color):
        pos = esper.try_component(target_entity, Position)
        if pos:
            # Create a new entity for FCT with the same position but separate lifecycle
            esper.create_entity(
                MapBound(),
                Position(pos.x, pos.y, pos.layer),
                FCT(
                    text=text,
                    color=color,
                    vx=random.uniform(-0.5, 0.5),
                    vy=-1.5,
                    ttl=1.0,
                    max_ttl=1.0
                )
            )

    def _get_name(self, entity):
        try:
            return esper.component_for_entity(entity, Name).name
        except KeyError:
            return f"Entity {entity}"

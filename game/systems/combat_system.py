import random

import esper

from config import (
    BLEED_DAMAGE_PER_TURN,
    BLEED_TURNS,
    COMBAT_CRIT_CHANCE,
    COMBAT_CRIT_MULTIPLIER,
    COMBAT_DAMAGE_VARIANCE,
    COMBAT_MIN_DAMAGE,
    LogCategory,
)
from game.components import (
    FCT,
    AIBehaviorState,
    AttackIntent,
    Bleeding,
    EffectiveStats,
    MapBound,
    Name,
    PlayerTag,
    Position,
    Stats,
)


class CombatSystem(esper.Processor):
    def __init__(self, action_system=None, rng: random.Random | None = None):
        super().__init__()
        self.action_system = action_system
        # Injectable for deterministic tests; bootstrap leaves the default.
        self.rng = rng or random.Random()

    def process(self, *args, **kwargs):
        for attacker, intent in list(esper.get_component(AttackIntent)):
            target = intent.target_entity

            attacker_stats = esper.try_component(attacker, Stats)
            target_stats = esper.try_component(target, Stats)

            if attacker_stats and target_stats:
                # Use EffectiveStats for calculations if available, fall back to base Stats
                attacker_eff = esper.try_component(attacker, EffectiveStats) or attacker_stats
                target_eff = esper.try_component(target, EffectiveStats) or target_stats

                # Calculate damage using effective values; abilities may
                # scale the attacker's power (G5). A connecting hit (power > 0)
                # rolls +-COMBAT_DAMAGE_VARIANCE and always chips at least
                # COMBAT_MIN_DAMAGE so defense never produces a stalemate turn.
                attack_power = round(attacker_eff.power * intent.power_multiplier)
                if attack_power > 0:
                    # r in [0,1]; r == 0.5 -> factor 1.0
                    factor = 1.0 + COMBAT_DAMAGE_VARIANCE * (2 * self.rng.random() - 1)
                    raw = round(attack_power * factor) - target_eff.defense
                    damage = max(COMBAT_MIN_DAMAGE, raw)
                else:
                    damage = 0  # power-0 attackers (e.g. Deer) still deal nothing

                # Critical hit: double damage and an open, bleeding wound
                is_crit = damage > 0 and self.rng.random() < COMBAT_CRIT_CHANCE
                if is_crit:
                    damage *= COMBAT_CRIT_MULTIPLIER
                    esper.add_component(target, Bleeding(damage_per_turn=BLEED_DAMAGE_PER_TURN, turns_left=BLEED_TURNS))

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
                if is_crit:
                    esper.dispatch_event(
                        "log_message",
                        f"{attacker_name} lands a critical hit on {target_name} for {damage} damage — it bleeds!",
                        None,
                        category,
                    )
                    self._spawn_fct(target, f"{damage}!", (255, 160, 0))
                elif damage > 0:
                    esper.dispatch_event(
                        "log_message", f"{attacker_name} hits {target_name} for {damage} damage.", None, category
                    )
                    self._spawn_fct(target, str(damage), (255, 0, 0))
                else:
                    esper.dispatch_event(
                        "log_message", f"{attacker_name} attacks {target_name} but deals no damage.", None, category
                    )
                    self._spawn_fct(target, "0", (200, 200, 200))

                # Death Check
                # Use effective HP for death check to account for bonuses
                if target_eff.hp <= 0:
                    esper.dispatch_event("entity_died", target, attacker)

            # Remove AttackIntent
            esper.remove_component(attacker, AttackIntent)

    def _spawn_fct(self, target_entity, text, color):
        pos = esper.try_component(target_entity, Position)
        if pos:
            # Create a new entity for FCT with the same position but separate lifecycle
            esper.create_entity(
                MapBound(),
                Position(pos.x, pos.y, pos.layer),
                FCT(text=text, color=color, vx=random.uniform(-0.5, 0.5), vy=-1.5, ttl=1.0, max_ttl=1.0),
            )

    def _get_name(self, entity):
        try:
            return esper.component_for_entity(entity, Name).name
        except KeyError:
            return f"Entity {entity}"

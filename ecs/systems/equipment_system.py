import esper
from ecs.components import Stats, Equipment, EffectiveStats, StatModifiers
from config import DN_SETTINGS

class EquipmentSystem(esper.Processor):
    def __init__(self, world_clock):
        super().__init__()
        self.world_clock = world_clock

    def process(self, *args, **kwargs):
        # Fetch current phase and perception multiplier
        phase = self.world_clock.phase
        multiplier = DN_SETTINGS.get(phase, {}).get("perception", 1.0)

        for ent, stats in esper.get_component(Stats):
            # 1. Start with base values
            max_hp = stats.base_max_hp
            power = stats.base_power
            defense = stats.base_defense
            max_mana = stats.base_max_mana
            perception = stats.base_perception
            intelligence = stats.base_intelligence
            
            hp_bonus = 0
            mana_bonus = 0
            
            # 2. Iterate over equipped items if Equipment component exists
            if esper.has_component(ent, Equipment):
                equipment = esper.component_for_entity(ent, Equipment)
                for slot, item_id in equipment.slots.items():
                    if item_id is not None and esper.entity_exists(item_id):
                        if esper.has_component(item_id, StatModifiers):
                            mods = esper.component_for_entity(item_id, StatModifiers)
                            hp_bonus += mods.hp
                            max_hp += mods.hp
                            power += mods.power
                            defense += mods.defense
                            mana_bonus += mods.mana
                            max_mana += mods.mana
                            perception += mods.perception
                            intelligence += mods.intelligence

            # 3. Apply time-of-day multiplier to perception
            perception = max(1, int(perception * multiplier))
            
            # 4. Calculate current effective values
            # StatModifiers.hp applies to both max_hp and current hp.
            current_hp = stats.hp + hp_bonus
            current_mana = stats.mana + mana_bonus
            
            # 5. Update or create the EffectiveStats component
            if esper.has_component(ent, EffectiveStats):
                eff = esper.component_for_entity(ent, EffectiveStats)
                eff.hp = current_hp
                eff.max_hp = max_hp
                eff.power = power
                eff.defense = defense
                eff.mana = current_mana
                eff.max_mana = max_mana
                eff.perception = perception
                eff.intelligence = intelligence
            else:
                eff = EffectiveStats(
                    hp=current_hp,
                    max_hp=max_hp,
                    power=power,
                    defense=defense,
                    mana=current_mana,
                    max_mana=max_mana,
                    perception=perception,
                    intelligence=intelligence
                )
                esper.add_component(ent, eff)

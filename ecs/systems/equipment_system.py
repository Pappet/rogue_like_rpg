import esper
from ecs.components import Stats, Equipment, EffectiveStats, StatModifiers

class EquipmentSystem(esper.Processor):
    def process(self):
        for ent, (stats, equipment) in self.world.get_components(Stats, Equipment):
            # 1. Start with base values
            max_hp = stats.base_max_hp
            power = stats.base_power
            defense = stats.base_defense
            max_mana = stats.base_max_mana
            perception = stats.base_perception
            intelligence = stats.base_intelligence
            
            hp_bonus = 0
            mana_bonus = 0
            
            # 2. Iterate over equipped items
            for slot, item_id in equipment.slots.items():
                if item_id is not None and self.world.entity_exists(item_id):
                    if self.world.has_component(item_id, StatModifiers):
                        mods = self.world.component_for_entity(item_id, StatModifiers)
                        hp_bonus += mods.hp
                        max_hp += mods.hp
                        power += mods.power
                        defense += mods.defense
                        mana_bonus += mods.mana
                        max_mana += mods.mana
                        perception += mods.perception
                        intelligence += mods.intelligence
            
            # 3. Calculate current effective values
            # StatModifiers.hp applies to both max_hp and current hp.
            current_hp = stats.hp + hp_bonus
            current_mana = stats.mana + mana_bonus
            
            # 4. Update or create the EffectiveStats component
            if self.world.has_component(ent, EffectiveStats):
                eff = self.world.component_for_entity(ent, EffectiveStats)
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
                self.world.add_component(ent, eff)

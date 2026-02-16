"""Entity factory module.

Provides EntityFactory which creates ECS entities from EntityTemplate registry data.
This mirrors the data-driven approach used for tiles in Phase 9.
"""

from config import SpriteLayer
from ecs.components import Position, Renderable, Stats, Name, Blocker, AI, Description, AIBehaviorState, AIState, Alignment, LootTable
from entities.entity_registry import EntityRegistry


class EntityFactory:
    """Factory that creates ECS entities from registry templates."""

    @staticmethod
    def create(world, template_id: str, x: int, y: int) -> int:
        """Create an ECS entity from a registered template.

        Args:
            world: The esper ECS world instance.
            template_id: The entity template ID to look up in EntityRegistry.
            x: The x-coordinate for the entity's Position.
            y: The y-coordinate for the entity's Position.

        Returns:
            The integer entity ID created in the world.

        Raises:
            ValueError: If template_id is not found in the EntityRegistry.
        """
        template = EntityRegistry.get(template_id)
        if template is None:
            raise ValueError(
                f"Entity template '{template_id}' not found in EntityRegistry. "
                f"Ensure ResourceLoader.load_entities() has been called and the "
                f"template ID is correct. Available IDs: {EntityRegistry.all_ids()}"
            )

        # Convert sprite_layer string to SpriteLayer enum value
        layer_value = SpriteLayer[template.sprite_layer].value

        components = [
            Position(x, y),
            Renderable(template.sprite, layer_value, template.color),
            Stats(
                hp=template.hp,
                max_hp=template.max_hp,
                power=template.power,
                defense=template.defense,
                mana=template.mana,
                max_mana=template.max_mana,
                perception=template.perception,
                intelligence=template.intelligence,
                base_hp=template.hp,
                base_max_hp=template.max_hp,
                base_power=template.power,
                base_defense=template.defense,
                base_mana=template.mana,
                base_max_mana=template.max_mana,
                base_perception=template.perception,
                base_intelligence=template.intelligence,
            ),
            Name(template.name),
        ]

        if template.blocker:
            components.append(Blocker())

        if template.ai:
            components.append(AI())
            components.append(AIBehaviorState(
                state=AIState(template.default_state),
                alignment=Alignment(template.alignment),
            ))

        if template.description:
            components.append(
                Description(
                    base=template.description,
                    wounded_text=template.wounded_text,
                    wounded_threshold=template.wounded_threshold,
                )
            )

        if template.loot_table:
            # Convert list of lists [id, chance] to list of tuples (id, chance)
            entries = [(entry[0], float(entry[1])) for entry in template.loot_table]
            components.append(LootTable(entries=entries))

        return world.create_entity(*components)

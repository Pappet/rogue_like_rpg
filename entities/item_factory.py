from entities.item_registry import ItemRegistry
from ecs.components import Name, Renderable, Portable, ItemMaterial, StatModifiers, Position, Equippable, SlotType, Consumable, Description
from config import SpriteLayer

class ItemFactory:
    @staticmethod
    def create(world, template_id: str) -> int:
        """Create an item entity without a Position.
        
        Args:
            world: The ECS world.
            template_id: The ID of the item template to use.
            
        Returns:
            The entity ID of the newly created item.
        """
        template = ItemRegistry.get(template_id)
        if not template:
            raise ValueError(f"Item template '{template_id}' not found in ItemRegistry.")

        entity = world.create_entity()
        
        world.add_component(entity, Name(name=template.name))
        
        # Convert sprite_layer string to SpriteLayer enum value
        try:
            layer_enum = SpriteLayer[template.sprite_layer]
            layer_value = layer_enum.value
        except (KeyError, AttributeError):
            # Fallback if the string doesn't match an enum member
            layer_value = SpriteLayer.ITEMS.value
            
        world.add_component(entity, Renderable(
            sprite=template.sprite,
            layer=layer_value,
            color=template.color
        ))
        
        world.add_component(entity, Portable(weight=template.weight))
        world.add_component(entity, ItemMaterial(material=template.material))
        world.add_component(entity, Description(base=template.description))

        if template.slot:
            world.add_component(entity, Equippable(slot=SlotType(template.slot)))
        
        if template.stats:
            world.add_component(entity, StatModifiers(
                hp=template.stats.get("hp", 0),
                power=template.stats.get("power", 0),
                defense=template.stats.get("defense", 0),
                mana=template.stats.get("mana", 0),
                perception=template.stats.get("perception", 0),
                intelligence=template.stats.get("intelligence", 0)
            ))
        
        if template.consumable:
            world.add_component(entity, Consumable(
                effect_type=template.consumable.get("effect_type"),
                amount=template.consumable.get("amount", 0),
                consumed_on_use=template.consumable.get("consumed_on_use", True)
            ))
            
        return entity

    @staticmethod
    def create_on_ground(world, template_id: str, x: int, y: int, layer: int = 0) -> int:
        """Create an item entity and place it on the ground at (x, y).
        
        Args:
            world: The ECS world.
            template_id: The ID of the item template to use.
            x: X-coordinate.
            y: Y-coordinate.
            layer: Map layer.
            
        Returns:
            The entity ID of the newly created item.
        """
        entity = ItemFactory.create(world, template_id)
        world.add_component(entity, Position(x=x, y=y, layer=layer))
        return entity

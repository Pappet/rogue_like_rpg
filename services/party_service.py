import esper
from ecs.components import Position, Renderable, Stats, Name, Inventory, TurnOrder, ActionList, Action, Blocker
from config import SpriteLayer

class PartyService:
    def __init__(self):
        pass

    def create_initial_party(self, x: int, y: int):
        # Create player entity in ECS
        player_entity = esper.create_entity(
            Position(x, y),
            Renderable("@", SpriteLayer.ENTITIES.value, (255, 255, 255)),
            Stats(
                hp=100, max_hp=100, power=5, defense=2, mana=50, max_mana=50, perception=10, intelligence=10,
                base_hp=100, base_max_hp=100, base_power=5, base_defense=2, base_mana=50, base_max_mana=50, base_perception=10, base_intelligence=10
            ),
            Name("Player"),
            Blocker(),
            Inventory(),
            TurnOrder(priority=0), # Player usually has high priority
            ActionList(actions=[
                Action(name="Move"),
                Action(name="Enter Portal"),
                Action(name="Investigate", range=10, requires_targeting=True, targeting_mode="inspect"),
                Action(name="Ranged", range=5, requires_targeting=True, targeting_mode="auto"),
                Action(name="Spells", cost_mana=10, range=7, requires_targeting=True, targeting_mode="manual"),
                Action(name="Items")
            ])
        )
        
        # We could create more heroes as separate entities or keep them in player's party
        # For now, let's just return the player entity
        return player_entity

def get_entity_closure(world, root_entity):
    """Find all entities that should travel with the root_entity (e.g., inventory items)."""
    closure = {root_entity}
    stack = [root_entity]
    
    while stack:
        current = stack.pop()
        try:
            inventory = world.component_for_entity(current, Inventory)
            for item_id in inventory.items:
                if item_id not in closure:
                    closure.add(item_id)
                    stack.append(item_id)
        except KeyError:
            # Entity doesn't have an inventory
            pass
    
    return list(closure)

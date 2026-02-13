import esper
from ecs.components import Position, Renderable, Stats, Name, Inventory, TurnOrder, ActionList, Action
from config import SpriteLayer

class PartyService:
    def __init__(self):
        pass

    def create_initial_party(self, x: int, y: int):
        # Create player entity in ECS
        player_entity = esper.create_entity(
            Position(x, y),
            Renderable("@", SpriteLayer.ENTITIES.value, (255, 255, 255)),
            Stats(hp=100, max_hp=100, power=5, defense=2, mana=50, max_mana=50, perception=10, intelligence=10),
            Name("Player"),
            Inventory(),
            TurnOrder(priority=0), # Player usually has high priority
            ActionList(actions=[
                Action(name="Move"),
                Action(name="Investigate"),
                Action(name="Ranged", range=5, requires_targeting=True, targeting_mode="auto"),
                Action(name="Spells", cost_mana=10, range=7, requires_targeting=True, targeting_mode="manual"),
                Action(name="Items")
            ])
        )
        
        # We could create more heroes as separate entities or keep them in player's party
        # For now, let's just return the player entity
        return player_entity
import esper
from ecs.components import Position, Renderable, Stats, Inventory, TurnOrder, ActionList
from config import SpriteLayer

class PartyService:
    def __init__(self):
        pass

    def create_initial_party(self, x: int, y: int):
        # Create player entity in ECS
        player_entity = esper.create_entity(
            Position(x, y),
            Renderable("@", SpriteLayer.ENTITIES.value, (255, 255, 255)),
            Stats(hp=100, max_hp=100, mana=50, max_mana=50, perception=10, intelligence=10),
            Inventory(),
            TurnOrder(priority=0), # Player usually has high priority
            ActionList(actions=["Move", "Investigate", "Ranged", "Spells", "Items"])
        )
        
        # We could create more heroes as separate entities or keep them in player's party
        # For now, let's just return the player entity
        return player_entity
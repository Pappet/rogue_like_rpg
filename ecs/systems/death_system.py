import esper
import random
import logging
from ecs.components import Name, Renderable, Blocker, AI, Corpse, Stats, AIBehaviorState, ChaseData, WanderData, LootTable, Position, PlayerTag
from config import SpriteLayer, LogCategory
from entities.item_factory import ItemFactory
from ecs.world import get_world
from ecs.systems.map_aware_system import MapAwareSystem

logger = logging.getLogger(__name__)

class DeathSystem(MapAwareSystem):
    def __init__(self):
        super().__init__()
        # Register the event handler for entity death
        esper.set_handler("entity_died", self.on_entity_died)

    def on_entity_died(self, entity):
        # --- Player death: dispatch event and return early ---
        if esper.has_component(entity, PlayerTag):
            logger.info("Player has died!")
            esper.dispatch_event("log_message", "[color=red]You have been slain![/color]")
            esper.dispatch_event("player_died")
            return

        name_comp = esper.try_component(entity, Name)
        if name_comp:
            entity_name = name_comp.name
            
            # Log message
            esper.dispatch_event("log_message", f"[color=orange]{entity_name}[/color] dies!")
            
            # Update Name
            name_comp.name = f"Remains of {entity_name}"
        else:
            esper.dispatch_event("log_message", "[color=orange]Something[/color] dies!")

        # --- Handle Loot Drops ---
        if esper.has_component(entity, LootTable):
            loot_table = esper.component_for_entity(entity, LootTable)
            pos = esper.try_component(entity, Position)
            if pos:
                self._handle_loot_drops(loot_table, pos)

        # Remove components that a corpse shouldn't have
        # Blocker: Corpses don't block movement
        # AI: Corpses don't take turns
        # Stats: Corpses don't have health/combat stats (optional, but requested in plan context)
        for component_type in [Blocker, AI, Stats, AIBehaviorState, ChaseData, WanderData, LootTable]:
            if esper.has_component(entity, component_type):
                esper.remove_component(entity, component_type)

        # Update Renderable to look like a corpse
        renderable = esper.try_component(entity, Renderable)
        if renderable:
            renderable.sprite = "%"
            renderable.color = (139, 0, 0) # Dark Red
            renderable.layer = SpriteLayer.CORPSES.value

        # Add Corpse tag component
        esper.add_component(entity, Corpse())

    def _handle_loot_drops(self, loot_table, pos):
        """Roll for loot and spawn items, scattering if needed."""
        world = get_world()
        for template_id, chance in loot_table.entries:
            if random.random() < chance:
                # Find a valid position for the loot
                drop_x, drop_y = self._find_drop_position(pos.x, pos.y)
                ItemFactory.create_on_ground(world, template_id, drop_x, drop_y, pos.layer)
                esper.dispatch_event("log_message", f"The {template_id} drops to the ground.", None, LogCategory.LOOT)

    def _find_drop_position(self, x, y):
        """Return (x, y) if walkable, else search 8 neighbors."""
        if self._map_container and self._map_container.is_walkable(x, y):
            return x, y
        
        # Search neighbors if center is blocked
        neighbors = [
            (x-1, y-1), (x, y-1), (x+1, y-1),
            (x-1, y),           (x+1, y),
            (x-1, y+1), (x, y+1), (x+1, y+1)
        ]
        random.shuffle(neighbors)
        
        for nx, ny in neighbors:
            if self._map_container and self._map_container.is_walkable(nx, ny):
                return nx, ny
                
        # Fallback to original position if all neighbors are blocked
        return x, y


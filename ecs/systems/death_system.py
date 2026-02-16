import esper
import random
from ecs.components import Name, Renderable, Blocker, AI, Corpse, Stats, AIBehaviorState, ChaseData, WanderData, LootTable, Position
from config import SpriteLayer
from entities.item_factory import ItemFactory

class DeathSystem(esper.Processor):
    def __init__(self):
        super().__init__()
        self.map_container = None
        # Register the event handler for entity death
        esper.set_handler("entity_died", self.on_entity_died)

    def set_map(self, map_container):
        """Set the map container reference for loot scattering checks."""
        self.map_container = map_container

    def on_entity_died(self, entity):
        try:
            name_comp = esper.component_for_entity(entity, Name)
            entity_name = name_comp.name
            
            # Log message
            esper.dispatch_event("log_message", f"[color=orange]{entity_name}[/color] dies!")
            
            # Update Name
            name_comp.name = f"Remains of {entity_name}"
        except KeyError:
            entity_name = "Unknown"
            esper.dispatch_event("log_message", "[color=orange]Something[/color] dies!")

        # --- Handle Loot Drops ---
        if esper.has_component(entity, LootTable):
            loot_table = esper.component_for_entity(entity, LootTable)
            try:
                pos = esper.component_for_entity(entity, Position)
                self._handle_loot_drops(loot_table, pos)
            except KeyError:
                pass # No position, no loot drops

        # Remove components that a corpse shouldn't have
        # Blocker: Corpses don't block movement
        # AI: Corpses don't take turns
        # Stats: Corpses don't have health/combat stats (optional, but requested in plan context)
        for component_type in [Blocker, AI, Stats, AIBehaviorState, ChaseData, WanderData, LootTable]:
            if esper.has_component(entity, component_type):
                esper.remove_component(entity, component_type)

        # Update Renderable to look like a corpse
        try:
            renderable = esper.component_for_entity(entity, Renderable)
            renderable.sprite = "%"
            renderable.color = (139, 0, 0) # Dark Red
            renderable.layer = SpriteLayer.CORPSES.value
        except KeyError:
            pass

        # Add Corpse tag component
        esper.add_component(entity, Corpse())

    def _handle_loot_drops(self, loot_table, pos):
        """Roll for loot and spawn items, scattering if needed."""
        for template_id, chance in loot_table.entries:
            if random.random() < chance:
                # Find a valid position for the loot
                drop_x, drop_y = self._find_drop_position(pos.x, pos.y)
                ItemFactory.create_on_ground(self.world, template_id, drop_x, drop_y, pos.layer)
                esper.dispatch_event("log_message", f"The {template_id} drops to the ground.")

    def _find_drop_position(self, x, y):
        """Return (x, y) if walkable, else search 8 neighbors."""
        if self.map_container and self.map_container.is_walkable(x, y):
            return x, y
        
        # Search neighbors if center is blocked
        neighbors = [
            (x-1, y-1), (x, y-1), (x+1, y-1),
            (x-1, y),           (x+1, y),
            (x-1, y+1), (x, y+1), (x+1, y+1)
        ]
        random.shuffle(neighbors)
        
        for nx, ny in neighbors:
            if self.map_container and self.map_container.is_walkable(nx, ny):
                return nx, ny
                
        # Fallback to original position if all neighbors are blocked
        return x, y

    def process(self):
        # This processor reacts to events, so it doesn't need to do anything per frame
        pass

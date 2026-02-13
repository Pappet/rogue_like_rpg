import esper
from ecs.components import Name, Renderable, Blocker, AI, Corpse, Stats
from config import SpriteLayer

class DeathSystem(esper.Processor):
    def __init__(self):
        super().__init__()
        # Register the event handler for entity death
        esper.set_handler("entity_died", self.on_entity_died)

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

        # Remove components that a corpse shouldn't have
        # Blocker: Corpses don't block movement
        # AI: Corpses don't take turns
        # Stats: Corpses don't have health/combat stats (optional, but requested in plan context)
        for component_type in [Blocker, AI, Stats]:
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

    def process(self):
        # This processor reacts to events, so it doesn't need to do anything per frame
        pass

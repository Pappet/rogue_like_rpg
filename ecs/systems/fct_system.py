import esper
from ecs.components import FCT

class FCTSystem(esper.Processor):
    def process(self, dt, *args, **kwargs):
        """
        Processes the lifecycle and movement of Floating Combat Text entities.
        
        Args:
            dt: Delta time in seconds.
        """
        # We use a list to avoid issues with deleting entities during iteration
        for ent, fct in list(esper.get_component(FCT)):
            # Update offsets
            fct.offset_x += fct.vx * dt * 60
            fct.offset_y += fct.vy * dt * 60
            
            # Update TTL
            fct.ttl -= dt
            
            # If ttl <= 0, delete the entity from the world
            if fct.ttl <= 0:
                esper.delete_entity(ent)

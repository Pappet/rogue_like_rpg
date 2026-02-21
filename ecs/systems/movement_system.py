import esper
from ecs.components import Position, MovementRequest, Blocker, Stats, AttackIntent
from map.map_container import MapContainer
from services.interaction_resolver import InteractionResolver, InteractionType
from ecs.systems.map_aware_system import MapAwareSystem

class MovementSystem(esper.Processor, MapAwareSystem):
    def __init__(self, action_system=None):
        esper.Processor.__init__(self)
        MapAwareSystem.__init__(self)
        self.action_system = action_system

    def process(self, *args, **kwargs):
        # We use a list to avoid issues with modifying components during iteration
        for ent, (pos, req) in list(esper.get_components(Position, MovementRequest)):
            new_x = pos.x + req.dx
            new_y = pos.y + req.dy
            
            blocker_ent = self._get_blocker_at(new_x, new_y, pos.layer)
            
            if blocker_ent:
                # Use InteractionResolver to handle the collision
                interaction = InteractionResolver.resolve(esper, ent, blocker_ent)
                
                if interaction != InteractionType.NONE:
                    InteractionResolver.execute(esper, interaction, ent, blocker_ent, self.action_system)
                    # Consume the movement request without moving
                    esper.remove_component(ent, MovementRequest)
                    continue

            if self._is_walkable(new_x, new_y, pos.layer) and not blocker_ent:
                pos.x = new_x
                pos.y = new_y
            
            # Remove the request after processing
            esper.remove_component(ent, MovementRequest)

    def _is_walkable(self, x, y, layer_idx):
        if not self._map_container:
            return False
        tile = self._map_container.get_tile(x, y, layer_idx)
        return tile.walkable if tile else False

    def _get_blocker_at(self, x, y, layer_idx):
        for ent, (pos, blocker) in esper.get_components(Position, Blocker):
            if pos.x == x and pos.y == y and pos.layer == layer_idx:
                return ent
        return None

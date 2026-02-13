import esper
from ecs.components import Position, MovementRequest, Blocker, Stats, AttackIntent
from map.map_container import MapContainer

class MovementSystem(esper.Processor):
    def __init__(self, map_container: MapContainer):
        self.map_container = map_container

    def process(self):
        # We use a list to avoid issues with modifying components during iteration
        for ent, (pos, req) in list(esper.get_components(Position, MovementRequest)):
            new_x = pos.x + req.dx
            new_y = pos.y + req.dy
            
            blocker_ent = self._get_blocker_at(new_x, new_y)
            
            if blocker_ent:
                # If blocked by entity with Stats, it's an attack
                if esper.has_component(blocker_ent, Stats):
                    esper.add_component(ent, AttackIntent(target_entity=blocker_ent))
                    # Consume the movement request without moving
                    esper.remove_component(ent, MovementRequest)
                    continue

            if self._is_walkable(new_x, new_y) and not blocker_ent:
                pos.x = new_x
                pos.y = new_y
            
            # Remove the request after processing
            esper.remove_component(ent, MovementRequest)

    def _is_walkable(self, x, y):
        if self.map_container and self.map_container.layers:
            layer = self.map_container.layers[0] # Assume first layer for collision
            if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[0]):
                return layer.tiles[y][x].walkable
        return False

    def _get_blocker_at(self, x, y):
        for ent, (pos, blocker) in esper.get_components(Position, Blocker):
            if pos.x == x and pos.y == y:
                return ent
        return None
